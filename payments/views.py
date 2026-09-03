import json
import uuid
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from packages.models import Package
from .models import Payment
from .services import (
    validate_tanzania_phone,
    get_clickpesa_token,
    preview_clickpesa_ussd_push,
    initiate_clickpesa_ussd_push,
    query_clickpesa_payment,
)

# ============================================================================
# MAKE PAYMENT
# ============================================================================

@login_required
def make_payment(request, package_id):
    package = get_object_or_404(Package, id=package_id)

    if request.method != "POST":
        return render(request, "payments/pay.html", {"package": package})

    decoder_number = request.POST.get("decoder_number", "").strip()
    payment_phone = request.POST.get("payment_phone", "").strip()

    if not validate_tanzania_phone(payment_phone):
        messages.error(request, "Invalid Tanzania phone number.")
        return redirect("make_payment", package.id)

    # Format phone: 0712345678 -> 255712345678
    if payment_phone.startswith("0"):
        formatted_phone = f"255{payment_phone[-9:]}"
    elif payment_phone.startswith("+255"):
        formatted_phone = payment_phone[1:]
    elif payment_phone.startswith("255"):
        formatted_phone = payment_phone
    else:
        messages.error(request, "Phone format not supported.")
        return redirect("make_payment", package.id)

    token = get_clickpesa_token()
    if not token:
        messages.error(request, "Failed to authenticate payment system.")
        return redirect("make_payment", package.id)

    # Create local payment
    payment = Payment.objects.create(
        user=request.user,
        package=package,
        decoder_number=decoder_number,
        payment_phone=formatted_phone,
        amount=package.price,
        status="PENDING",
    )

    payment.order_reference = f"PAY{payment.id}{uuid.uuid4().hex[:8].upper()}"
    payment.save()

    # STEP 1: Preview USSD Push
    preview_result = preview_clickpesa_ussd_push(
        token=token,
        amount=str(int(payment.amount)),
        order_reference=payment.order_reference,
        phone_number=formatted_phone,
        fetch_sender_details=True,
    )

    if not preview_result["success"]:
        payment.status = "FAILED"
        payment.processed_at = timezone.now()
        payment.save()
        messages.error(request, f"Payment validation failed: {preview_result.get('message', 'Unknown error')}")
        return redirect("payment_status", payment.id)

    # Check available payment channels
    active_methods = preview_result.get("activeMethods", [])
    available_methods = [
        method for method in active_methods
        if str(method.get("status", "")).upper() == "AVAILABLE"
    ]

    if not available_methods:
        payment.status = "FAILED"
        payment.processed_at = timezone.now()
        payment.save()
        messages.error(request, "No payment method is currently available.")
        return redirect("payment_status", payment.id)

    # STEP 2: Initiate USSD Push
    initiate_result = initiate_clickpesa_ussd_push(
        token=token,
        amount=str(int(payment.amount)),
        order_reference=payment.order_reference,
        phone_number=formatted_phone,
    )

    if not initiate_result["success"]:
        payment.status = "FAILED"
        payment.processed_at = timezone.now()
        payment.save()
        messages.error(request, f"Payment failed: {initiate_result.get('message', 'Unknown error')}")
        return redirect("payment_status", payment.id)

    # Save transaction ID
    clickpesa_id = initiate_result.get("id")
    if clickpesa_id:
        payment.transaction_id = clickpesa_id

    # Update status based on ClickPesa response
    clickpesa_status = str(initiate_result.get("status", "PROCESSING")).upper()
    if clickpesa_status in ["SUCCESS", "SETTLED"]:
        payment.status = "PAID"
        payment.completed_at = timezone.now()
    elif clickpesa_status == "FAILED":
        payment.status = "FAILED"
        payment.processed_at = timezone.now()
    else:
        payment.status = "PROCESSING"

    payment.save()

    if payment.status == "PAID":
        messages.success(request, "Payment completed successfully.")
    elif payment.status == "FAILED":
        messages.error(request, "Payment failed.")
    else:
        messages.success(request, "USSD Push sent. Please check your phone and enter your PIN.")

    return redirect("payment_status", payment.id)

# ============================================================================
# PAYMENT STATUS
# ============================================================================

@login_required
def payment_status(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    return render(request, "payments/status.html", {"payment": payment})

# ============================================================================
# REFRESH PAYMENT STATUS
# ============================================================================

@login_required
def refresh_payment_status(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    if payment.status in ["PAID", "COMPLETED", "FAILED"]:
        return redirect("payment_status", payment.id)

    token = get_clickpesa_token()
    if not token:
        messages.error(request, "Unable to authenticate with ClickPesa.")
        return redirect("payment_status", payment.id)

    result = query_clickpesa_payment(token=token, order_reference=payment.order_reference)

    if not result["success"]:
        messages.error(request, result.get("message", "Unable to retrieve payment status."))
        return redirect("payment_status", payment.id)

    payments = result.get("data", [])
    if isinstance(payments, dict):
        payments = [payments]

    if not payments:
        messages.warning(request, "No payment information was returned.")
        return redirect("payment_status", payment.id)

    clickpesa_payment = payments[0]
    clickpesa_status = str(clickpesa_payment.get("status", "")).upper()
    transaction_id = clickpesa_payment.get("id") or clickpesa_payment.get("paymentReference")

    if transaction_id:
        payment.transaction_id = transaction_id

    if clickpesa_status in ["SUCCESS", "SETTLED"]:
        payment.status = "PAID"
        if not payment.completed_at:
            payment.completed_at = timezone.now()
    elif clickpesa_status == "FAILED":
        payment.status = "FAILED"
        if not payment.processed_at:
            payment.processed_at = timezone.now()
    elif clickpesa_status in ["PROCESSING", "PENDING"]:
        payment.status = "PROCESSING"

    payment.save()

    if payment.status == "PAID":
        messages.success(request, "Payment has been confirmed successfully.")
    elif payment.status == "FAILED":
        messages.error(request, "Payment failed.")
    else:
        messages.info(request, "Payment is still being processed.")

    return redirect("payment_status", payment.id)

# ============================================================================
# CLICKPESA CALLBACK / WEBHOOK
# ============================================================================

@csrf_exempt
def clickpesa_callback(request):
    if request.method == "GET":
        return JsonResponse({"success": True, "message": "Callback endpoint active."})

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Only POST allowed"}, status=405)

    try:
        body = request.body.decode("utf-8")
        if not body:
            return JsonResponse({"success": False, "message": "Empty body"}, status=400)

        data = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)
    except:
        return JsonResponse({"success": False, "message": "Server error"}, status=500)

    # Normalize data
    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    if isinstance(data, list):
        if not data:
            return JsonResponse({"success": False, "message": "Empty callback data"}, status=400)
        data = data[0]

    if not isinstance(data, dict):
        return JsonResponse({"success": False, "message": "Invalid callback format"}, status=400)

    # Get payment info
    order_reference = data.get("orderReference") or data.get("order_reference")
    status = str(data.get("status", "")).upper()
    transaction_id = data.get("id") or data.get("transactionId") or data.get("paymentReference")

    if not order_reference:
        return JsonResponse({"success": False, "message": "Missing order reference"}, status=400)

    payment = Payment.objects.filter(order_reference=order_reference).first()
    if not payment:
        return JsonResponse({"success": False, "message": "Payment not found"}, status=404)

    if transaction_id:
        payment.transaction_id = transaction_id

    if status in ["SUCCESS", "SETTLED"]:
        payment.status = "PAID"
        if not payment.completed_at:
            payment.completed_at = timezone.now()
    elif status in ["FAILED", "FAILURE", "DECLINED", "REJECTED", "ERROR"]:
        payment.status = "FAILED"
        if not payment.processed_at:
            payment.processed_at = timezone.now()
    elif status in ["PROCESSING", "PENDING"]:
        payment.status = "PROCESSING"

    payment.save()

    return JsonResponse({
        "success": True,
        "status": payment.status,
        "orderReference": payment.order_reference,
    })

# ============================================================================
# PAYMENTS LIST
# ============================================================================

@login_required
def payments_list(request):
    payments = Payment.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "payments/payments.html", {"payments": payments})

# ============================================================================
# ADMIN TRANSACTIONS
# ============================================================================

@login_required
def transactions(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Forbidden")
    
    payments = Payment.objects.all().order_by("-created_at")
    return render(request, "payments/transactions.html", {"payments": payments})

# ============================================================================
# ADMIN DASHBOARD
# ============================================================================

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect("dashboard")
    
    return render(request, "admin/payments_dashboard.html", {
        "pending": Payment.objects.filter(status="PENDING").order_by("-created_at"),
        "processing": Payment.objects.filter(status="PROCESSING").order_by("-created_at"),
        "paid": Payment.objects.filter(status="PAID").order_by("-created_at"),
        "completed": Payment.objects.filter(status="COMPLETED").order_by("-created_at"),
        "failed": Payment.objects.filter(status="FAILED").order_by("-created_at"),
    })

# ============================================================================
# ADMIN ACTIONS
# ============================================================================

@login_required
def start_processing(request, payment_id):
    if not request.user.is_staff:
        return redirect("dashboard")
    
    payment = get_object_or_404(Payment, id=payment_id)
    payment.status = "PROCESSING"
    payment.processed_at = timezone.now()
    payment.save()
    
    messages.success(request, "Payment moved to processing.")
    return redirect("admin_dashboard")

@login_required
def mark_completed(request, payment_id):
    if not request.user.is_staff:
        return redirect("dashboard")
    
    payment = get_object_or_404(Payment, id=payment_id)
    payment.status = "COMPLETED"
    payment.completed_at = timezone.now()
    payment.save()
    
    messages.success(request, "Package activated successfully.")
    return redirect("admin_dashboard")