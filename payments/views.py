import json
import logging
import uuid
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from packages.models import Package, DecoderType
from .models import Payment, PaymentItem
from .services import (
    validate_tanzania_phone,
    normalize_tanzania_phone,
    get_clickpesa_token,
    initiate_clickpesa_ussd_push,
    query_clickpesa_payment,
    extract_gateway_record,
    get_gateway_status,
    get_gateway_transaction_id,
    get_gateway_amount,
    get_gateway_currency,
    classify_gateway_status,
)

logger = logging.getLogger("payments")


# ============================================================================
# HELPERS
# ============================================================================

def generate_order_reference():
    return f"PAY{uuid.uuid4().hex[:12].upper()}"


def sync_payment_from_gateway_data(payment, gateway_data):
    """Sync local payment from verified gateway data."""
    data = extract_gateway_record(gateway_data)
    if not data:
        return {"updated": False, "reason": "Invalid gateway data"}

    gateway_status = get_gateway_status(data)
    gateway_category = classify_gateway_status(gateway_status)
    gateway_amount = get_gateway_amount(data)
    gateway_currency = get_gateway_currency(data)
    txn_id = get_gateway_transaction_id(data)

    # Save metadata
    if gateway_status:
        payment.gateway_status = gateway_status[:50]
    if txn_id:
        payment.transaction_id = str(txn_id)[:100]

    msg = data.get("message") or data.get("description") or ""
    if msg:
        payment.gateway_message = str(msg)[:500]

    payment.last_checked_at = timezone.now()

    # Verify amount and currency
    amount_mismatch = gateway_amount is not None and gateway_amount != payment.amount
    currency_mismatch = gateway_currency and gateway_currency != payment.currency.upper()

    if amount_mismatch or currency_mismatch:
        if amount_mismatch:
            logger.warning(f"Amount mismatch for {payment.order_reference}")
        if currency_mismatch:
            logger.warning(f"Currency mismatch for {payment.order_reference}")

        if payment.status != Payment.REVIEW:
            reason = []
            if amount_mismatch:
                reason.append("amount mismatch")
            if currency_mismatch:
                reason.append("currency mismatch")
            payment.mark_review(", ".join(reason))
        payment.requires_review = True
        payment.save()
        return {"updated": True, "status": payment.status, "requires_review": True}

    # Update status based on gateway category
    if gateway_category == "PAID":
        if payment.status in (Payment.PENDING, Payment.PROCESSING):
            payment.mark_paid()
            logger.info(f"Payment {payment.order_reference} → PAID")
    elif gateway_category == "FAILED":
        if payment.status in (Payment.PENDING, Payment.PROCESSING):
            payment.mark_failed()
            logger.info(f"Payment {payment.order_reference} → FAILED")
    elif gateway_category == "PROCESSING":
        if payment.status == Payment.PENDING:
            payment.mark_processing()
            logger.info(f"Payment {payment.order_reference} → PROCESSING")
    else:
        logger.warning(f"Unknown gateway status '{gateway_status}' for {payment.order_reference}")

    payment.save()
    return {"updated": True, "status": payment.status}


def activate_package(payment):
    """Activate package - idempotent."""
    if payment.status == Payment.COMPLETED:
        logger.info(f"Package already activated for {payment.order_reference}")
        return True

    if payment.status != Payment.PAID:
        logger.warning(f"Cannot activate package for {payment.order_reference}: status={payment.status}")
        return False

    # =====================================================================
    # REPLACE WITH YOUR ACTUAL BUSINESS LOGIC
    # =====================================================================
    # Example:
    # from subscriptions.models import Subscription
    # subscription = Subscription.objects.create(
    #     user=payment.user,
    #     package=payment.package,
    #     decoder_number=payment.decoder_number,
    #     payment=payment,
    #     expires_at=timezone.now() + timedelta(days=payment.package.duration_months * 30),
    # )
    # send_activation_sms(payment.user.phone_number, subscription)
    # =====================================================================

    logger.info(f"Activating package for {payment.order_reference}: {payment.package.name}")

    with transaction.atomic():
        p = Payment.objects.select_for_update().get(id=payment.id)
        if p.mark_completed():
            p.save()
            logger.info(f"Payment {payment.order_reference} → COMPLETED")
            return True
    return False


def get_payment_or_404(payment_id, user):
    return get_object_or_404(Payment, id=payment_id, user=user)


def is_staff(user):
    return user.is_authenticated and user.is_staff


# ============================================================================
# CUSTOMER: MAKE PAYMENT
# ============================================================================

# payments/views.py - Badilisha make_payment

@login_required
def make_payment(request, package_id):
    package = get_object_or_404(Package, id=package_id, is_active=True)

    if request.method != "POST":
        return render(request, "payments/pay.html", {"package": package})

    # Get decoders and months from form
    decoder_numbers = request.POST.getlist("decoder_number[]")
    months_list = request.POST.getlist("months[]")
    phone = request.POST.get("payment_phone", "").strip()

    # Validate decoders
    if not decoder_numbers or not any(d.strip() for d in decoder_numbers):
        messages.error(request, "At least one decoder number is required.")
        return redirect("make_payment", package.id)

    # Filter valid decoders
    valid_decoders = []
    for i, decoder in enumerate(decoder_numbers):
        decoder = decoder.strip()
        if decoder:
            try:
                months = int(months_list[i]) if i < len(months_list) else 1
            except (ValueError, IndexError):
                months = 1
            months = max(1, min(months, 12))  # Between 1 and 12
            valid_decoders.append({
                'decoder': decoder,
                'months': months,
            })

    if not valid_decoders:
        messages.error(request, "At least one valid decoder number is required.")
        return redirect("make_payment", package.id)

    # Validate phone
    if not validate_tanzania_phone(phone):
        messages.error(request, "Invalid phone number.")
        return redirect("make_payment", package.id)

    normalized_phone = normalize_tanzania_phone(phone)
    if not normalized_phone:
        messages.error(request, "Invalid phone number.")
        return redirect("make_payment", package.id)

    # Calculate total
    unit_price = Decimal(str(package.price))
    total_amount = sum(unit_price * d['months'] for d in valid_decoders)
    total_months = sum(d['months'] for d in valid_decoders)

    token = get_clickpesa_token()
    if not token:
        messages.error(request, "Payment system temporarily unavailable.")
        return redirect("make_payment", package.id)

    # Create payment with items
    try:
        with transaction.atomic():
            existing = Payment.objects.select_for_update().filter(
                user=request.user,
                package=package,
                status__in=[Payment.PENDING, Payment.PROCESSING],
            ).first()
            if existing:
                messages.info(request, "You already have a pending payment for this package.")
                return redirect("payment_status", existing.id)

            payment = Payment.objects.create(
                user=request.user,
                package=package,
                decoder_type=package.decoder_type,
                decoder_number=valid_decoders[0]['decoder'],
                payment_phone=normalized_phone,
                amount=total_amount,
                currency="TZS",
                status=Payment.PENDING,
                order_reference=generate_order_reference(),
                total_decoders=len(valid_decoders),
                total_months=total_months,
            )

            # Create payment items
            for d in valid_decoders:
                PaymentItem.objects.create(
                    payment=payment,
                    decoder_number=d['decoder'],
                    months=d['months'],
                    package=package,
                    unit_price=unit_price,
                    subtotal=unit_price * d['months'],
                )
    except IntegrityError:
        existing = Payment.objects.filter(
            user=request.user,
            package=package,
            status__in=[Payment.PENDING, Payment.PROCESSING],
        ).first()
        if existing:
            messages.info(request, "You already have a pending payment for this package.")
            return redirect("payment_status", existing.id)
        logger.exception("Payment creation failed")
        messages.error(request, "Unable to create payment. Please try again.")
        return redirect("make_payment", package.id)

    # Send USSD Push for total amount
    result = initiate_clickpesa_ussd_push(
        token=token,
        amount=payment.amount,
        order_reference=payment.order_reference,
        phone_number=payment.payment_phone,
    )

    if result.get("success"):
        with transaction.atomic():
            p = Payment.objects.select_for_update().get(id=payment.id)
            p.mark_processing()
            if result.get("transaction_id"):
                p.transaction_id = str(result.get("transaction_id"))[:100]
            p.save()
        messages.success(request, "USSD Push sent. Check your phone and enter your PIN.")
    elif result.get("ambiguous"):
        with transaction.atomic():
            p = Payment.objects.select_for_update().get(id=payment.id)
            p.mark_processing()
            p.gateway_message = str(result.get("message", "Processing"))[:500]
            p.save()
        messages.info(request, "Payment is being processed. Please wait for confirmation.")
    else:
        with transaction.atomic():
            p = Payment.objects.select_for_update().get(id=payment.id)
            p.mark_failed()
            p.gateway_message = str(result.get("message", "Payment failed"))[:500]
            p.save()
        messages.error(request, f"Payment failed: {result.get('message', 'Payment failed')}")

    return redirect("payment_status", payment.id)


# ============================================================================
# CUSTOMER: PAYMENT STATUS
# ============================================================================

@login_required
def payment_status(request, payment_id):
    payment = get_payment_or_404(payment_id, request.user)

    # AJAX refresh - only query if not final
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" and request.GET.get("refresh"):
        if payment.is_final:
            return JsonResponse({"status": payment.status, "status_display": payment.get_status_display()})

        token = get_clickpesa_token()
        if token:
            result = query_clickpesa_payment(token, payment.order_reference)
            if result.get("success"):
                with transaction.atomic():
                    p = Payment.objects.select_for_update().get(id=payment.id)
                    sync_payment_from_gateway_data(p, result.get("data"))
                    payment = p

        return JsonResponse({
            "status": payment.status,
            "status_display": payment.get_status_display(),
            "requires_review": payment.requires_review,
        })

    return render(request, "payments/status.html", {"payment": payment})


# ============================================================================
# CUSTOMER: RETRY PAYMENT
# ============================================================================

@require_POST
@login_required
def retry_payment(request, payment_id):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(id=payment_id, user=request.user).first()
        if not payment:
            return JsonResponse({"success": False, "message": "Payment not found"}, status=404)

        if payment.status not in (Payment.PENDING, Payment.FAILED):
            return JsonResponse({"success": False, "message": "Cannot retry this payment"}, status=400)

        old_ref = payment.order_reference

    token = get_clickpesa_token()
    if not token:
        return JsonResponse({"success": False, "message": "Payment system unavailable"}, status=503)

    # Check previous reference first
    query_result = query_clickpesa_payment(token, old_ref)
    if query_result.get("success"):
        with transaction.atomic():
            p = Payment.objects.select_for_update().get(id=payment.id)
            sync_result = sync_payment_from_gateway_data(p, query_result.get("data"))
            if p.status in (Payment.PAID, Payment.COMPLETED, Payment.REVIEW):
                return JsonResponse({
                    "success": True,
                    "status": p.status,
                    "message": "Previous payment already processed",
                })

    # Generate new reference
    with transaction.atomic():
        p = Payment.objects.select_for_update().get(id=payment.id)
        if p.status not in (Payment.PENDING, Payment.FAILED):
            return JsonResponse({"success": False, "message": "Cannot retry now"}, status=400)

        p.order_reference = generate_order_reference()
        p.status = Payment.PENDING
        p.requires_review = False
        p.review_reason = ""
        p.gateway_message = ""
        p.gateway_status = ""
        p.last_checked_at = None
        p.save()
        new_ref = p.order_reference
        amount = p.amount
        phone = p.payment_phone

    # Send new USSD
    result = initiate_clickpesa_ussd_push(token, amount, new_ref, phone)

    if result.get("success"):
        with transaction.atomic():
            p = Payment.objects.select_for_update().get(id=payment.id)
            p.mark_processing()
            if result.get("transaction_id"):
                p.transaction_id = str(result.get("transaction_id"))[:100]
            p.save()
        return JsonResponse({
            "success": True,
            "status": p.status,
            "message": "USSD Push sent again. Check your phone.",
        })

    if result.get("ambiguous"):
        with transaction.atomic():
            p = Payment.objects.select_for_update().get(id=payment.id)
            p.mark_processing()
            p.gateway_message = str(result.get("message", "Processing"))[:500]
            p.save()
        return JsonResponse({
            "success": True,
            "status": p.status,
            "message": "Payment is being processed. Wait for confirmation.",
        })

    with transaction.atomic():
        p = Payment.objects.select_for_update().get(id=payment.id)
        p.mark_failed()
        p.gateway_message = str(result.get("message", "Payment failed"))[:500]
        p.save()

    return JsonResponse({
        "success": False,
        "status": p.status,
        "message": result.get("message", "Payment failed"),
    }, status=400)


# ============================================================================
# CUSTOMER: PAYMENT LIST
# ============================================================================

@login_required
def payments_list(request):
    payments = Payment.objects.filter(user=request.user).select_related("package").order_by("-created_at")[:100]
    return render(request, "payments/payments.html", {"payments": payments})


# ============================================================================
# WEBHOOK
# ============================================================================

@csrf_exempt
@require_POST
def clickpesa_callback(request):
    """ClickPesa webhook - idempotent payment confirmation."""
    if not request.body:
        return JsonResponse({"success": False, "message": "Empty body"}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Webhook invalid JSON")
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

    data = extract_gateway_record(payload)
    if not data:
        logger.warning("Webhook invalid data")
        return JsonResponse({"success": False, "message": "Invalid data"}, status=400)

    order_ref = data.get("orderReference") or data.get("order_reference")
    if not order_ref:
        logger.warning("Webhook missing order reference")
        return JsonResponse({"success": False, "message": "Missing reference"}, status=400)

    gateway_status = get_gateway_status(data)
    if not gateway_status:
        logger.warning(f"Webhook missing status for {order_ref}")
        return JsonResponse({"success": False, "message": "Missing status"}, status=400)

    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(order_reference=order_ref).first()
        if not payment:
            logger.warning(f"Webhook: Payment not found: {order_ref}")
            return JsonResponse({"success": False, "message": "Payment not found"}, status=404)

        if payment.status == Payment.COMPLETED:
            payment.webhook_received_at = timezone.now()
            payment.webhook_processed = True
            payment.save(update_fields=["webhook_received_at", "webhook_processed"])
            logger.info(f"Duplicate webhook ignored for {order_ref}")
            return JsonResponse({"success": True, "status": payment.status, "message": "Already completed"})

        payment.webhook_received_at = timezone.now()
        sync_result = sync_payment_from_gateway_data(payment, data)
        payment.webhook_processed = True
        payment.save()

        # Activate package if PAID - outside transaction if external calls needed
        if payment.status == Payment.PAID:
            # For now, activate inside transaction
            activate_package(payment)

    logger.info(f"Webhook processed: {order_ref} → {payment.status}")
    return JsonResponse({"success": True, "status": payment.status, "orderReference": payment.order_reference})


# ============================================================================
# ADMIN
# ============================================================================

@login_required
def transactions(request):
    if not is_staff(request.user):
        return HttpResponseForbidden("Forbidden")
    payments = Payment.objects.select_related("user", "package").order_by("-created_at")
    paginator = Paginator(payments, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "payments/transactions.html", {"page_obj": page_obj})


@login_required
def admin_dashboard(request):
    if not is_staff(request.user):
        return redirect("dashboard")
    return render(request, "admin/payments_dashboard.html", {
        "pending_count": Payment.objects.filter(status=Payment.PENDING).count(),
        "processing_count": Payment.objects.filter(status=Payment.PROCESSING).count(),
        "paid_count": Payment.objects.filter(status=Payment.PAID).count(),
        "completed_count": Payment.objects.filter(status=Payment.COMPLETED).count(),
        "failed_count": Payment.objects.filter(status=Payment.FAILED).count(),
        "review_count": Payment.objects.filter(status=Payment.REVIEW).count(),
        "recent_payments": Payment.objects.select_related("user", "package").order_by("-created_at")[:20],
    })


@require_POST
@login_required
def start_processing(request, payment_id):
    if not is_staff(request.user):
        return redirect("dashboard")
    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(id=payment_id).first()
        if not payment:
            messages.error(request, "Payment not found")
            return redirect("admin_dashboard")
        if payment.mark_processing():
            payment.save()
            messages.success(request, "Payment moved to processing")
        else:
            messages.error(request, f"Invalid transition from {payment.status} to PROCESSING")
    return redirect("admin_dashboard")


@require_POST
@login_required
def mark_completed(request, payment_id):
    if not is_staff(request.user):
        return redirect("dashboard")
    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(id=payment_id).first()
        if not payment:
            messages.error(request, "Payment not found")
            return redirect("admin_dashboard")
        if payment.status != Payment.PAID:
            messages.error(request, "Only PAID can be marked COMPLETED")
            return redirect("admin_dashboard")
        if payment.mark_completed():
            payment.save()
            messages.success(request, "Payment marked completed")
        else:
            messages.error(request, "Cannot complete this payment")
    return redirect("admin_dashboard")


@require_POST
@login_required
def resolve_review(request, payment_id):
    if not is_staff(request.user):
        return redirect("dashboard")
    action = request.POST.get("action", "").lower().strip()
    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(id=payment_id).first()
        if not payment:
            messages.error(request, "Payment not found")
            return redirect("admin_dashboard")
        if payment.status != Payment.REVIEW:
            messages.error(request, "Payment not in review")
            return redirect("admin_dashboard")

        if action == "approve":
            if payment.mark_paid():
                payment.requires_review = False
                payment.review_reason = ""
                payment.save()
                messages.success(request, "Payment approved and marked PAID")
            else:
                messages.error(request, "Cannot approve")
        elif action == "reject":
            if payment.mark_failed():
                payment.requires_review = False
                payment.save()
                messages.success(request, "Payment rejected and marked FAILED")
            else:
                messages.error(request, "Cannot reject")
        else:
            messages.error(request, "Invalid action")
    return redirect("admin_dashboard")