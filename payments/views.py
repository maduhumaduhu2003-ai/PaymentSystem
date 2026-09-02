import uuid
import requests
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from packages.models import Package
from .models import Payment
from .services import validate_tanzania_phone, get_clickpesa_token


# ============================================================================
# MAKE PAYMENT
# ============================================================================

@login_required
def make_payment(request, package_id):
    package = get_object_or_404(Package, id=package_id)

    if request.method == 'POST':
        decoder_number = request.POST.get('decoder_number', '').strip()
        payment_phone = request.POST.get('payment_phone', '').strip()

        # Validate phone
        if not validate_tanzania_phone(payment_phone):
            messages.error(request, 'Invalid Tanzania phone number')
            return redirect('make_payment', package.id)

        # Format phone
        if payment_phone.startswith('0'):
            formatted_phone = f"255{payment_phone[-9:]}"
        elif payment_phone.startswith('255'):
            formatted_phone = payment_phone
        else:
            messages.error(request, 'Phone format not supported')
            return redirect('make_payment', package.id)

        # Get token
        token = get_clickpesa_token()
        if not token:
            messages.error(request, 'Failed to authenticate payment system')
            return redirect('make_payment', package.id)

        # Create payment
        payment = Payment.objects.create(
            user=request.user,
            package=package,
            decoder_number=decoder_number,
            payment_phone=formatted_phone,
            amount=package.price,
            status='PENDING'
        )

        # Create order reference
        payment.order_reference = f"PAY{payment.id}{uuid.uuid4().hex[:8].upper()}"
        payment.save()

        # Send to ClickPesa
        url = "https://api.clickpesa.com/third-parties/payments/initiate-ussd-push-request"
        
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        
        payload = {
            "amount": str(int(payment.amount)),
            "currency": "TZS",
            "orderReference": payment.order_reference,
            "phoneNumber": formatted_phone,
            "callbackUrl": settings.CLICKPESA_CALLBACK_URL
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                messages.success(request, 'PIN sent to your phone')
            else:
                payment.status = 'FAILED'
                payment.save()
                messages.error(request, f'Payment failed')
                
        except:
            payment.status = 'FAILED'
            payment.save()
            messages.error(request, 'Payment gateway error')

        return redirect('payment_status', payment.id)

    return render(request, 'payments/pay.html', {'package': package})


# ============================================================================
# PAYMENT STATUS
# ============================================================================

@login_required
def payment_status(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    return render(request, 'payments/status.html', {'payment': payment})


# ============================================================================
# CLICKPESA CALLBACK
# ============================================================================

@csrf_exempt
def clickpesa_callback(request):
    if request.method == 'GET':
        return JsonResponse({'message': 'Callback endpoint active'})
    
    if request.method != 'POST':
        return JsonResponse({'message': 'Only POST allowed'}, status=405)

    try:
        body = request.body.decode('utf-8')
        if not body:
            return JsonResponse({'message': 'Empty body'}, status=400)

        data = json.loads(body)
        
        # Handle nested data
        if isinstance(data, dict) and 'data' in data:
            data = data['data']
        
        if isinstance(data, list) and data:
            data = data[0]

        order_reference = data.get('orderReference') or data.get('order_reference')
        status = data.get('status', '').upper()
        transaction_id = data.get('id') or data.get('transactionId')

        if not order_reference:
            return JsonResponse({'message': 'Missing order reference'}, status=400)

        payment = Payment.objects.filter(order_reference=order_reference).first()
        
        if not payment:
            return JsonResponse({'message': 'Payment not found'}, status=404)

        # Map ClickPesa status to local status
        if status == 'SUCCESS':
            payment.status = 'PAID'
            payment.completed_at = timezone.now()
        elif status in ['FAILED', 'FAILURE', 'DECLINED', 'REJECTED', 'ERROR']:
            payment.status = 'FAILED'
            payment.processed_at = timezone.now()
        elif status in ['PROCESSING', 'PENDING']:
            payment.status = 'PROCESSING'

        if transaction_id:
            payment.transaction_id = transaction_id

        payment.save()

        return JsonResponse({'success': True, 'status': payment.status})

    except Exception as e:
        return JsonResponse({'message': 'Server error'}, status=500)


# ============================================================================
# PAYMENTS LIST
# ============================================================================

@login_required
def payments_list(request):
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'payments/payments.html', {'payments': payments})


# ============================================================================
# ADMIN TRANSACTIONS
# ============================================================================

@login_required
def transactions(request):
    if not request.user.is_staff:
        return HttpResponseForbidden('Forbidden')
    
    payments = Payment.objects.all().order_by('-created_at')
    return render(request, 'payments/transactions.html', {'payments': payments})


# ============================================================================
# ADMIN DASHBOARD
# ============================================================================

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    return render(request, 'admin/payments_dashboard.html', {
        'pending': Payment.objects.filter(status='PENDING').order_by('-created_at'),
        'processing': Payment.objects.filter(status='PROCESSING').order_by('-created_at'),
        'paid': Payment.objects.filter(status='PAID').order_by('-created_at'),
        'completed': Payment.objects.filter(status='COMPLETED').order_by('-created_at'),
        'failed': Payment.objects.filter(status='FAILED').order_by('-created_at'),
    })


# ============================================================================
# ADMIN ACTIONS
# ============================================================================

@login_required
def start_processing(request, payment_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    payment = get_object_or_404(Payment, id=payment_id)
    payment.status = 'PROCESSING'
    payment.processed_at = timezone.now()
    payment.save()
    
    messages.success(request, 'Payment moved to processing')
    return redirect('admin_dashboard')


@login_required
def mark_completed(request, payment_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    payment = get_object_or_404(Payment, id=payment_id)
    payment.status = 'COMPLETED'
    payment.completed_at = timezone.now()
    payment.save()
    
    messages.success(request, 'Package activated successfully')
    return redirect('admin_dashboard')