from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta

from packages.models import Package, DecoderType
from payments.models import Payment
from .models import Business, BusinessPayment
from accounts.models import User


# ============================================================================
# BUSINESS DASHBOARD
# ============================================================================

@login_required
def dashboard(request):
    """Business Owner Dashboard"""
    
    if not request.user.is_business_owner:
        messages.error(request, "Access denied.")
        return redirect('/packages/')
    
    business, created = Business.objects.get_or_create(
        user=request.user,
        defaults={
            'business_name': request.user.business_name or "My Business",
            'business_address': request.user.business_address or "",
        }
    )
    
    today = timezone.now().date()
    today_sales = Payment.objects.filter(created_at__date=today)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    context = {
        'business': business,
        'total_sales': Payment.objects.count(),
        'total_revenue': Payment.objects.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0,
        'today_revenue': today_sales.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0,
        'today_count': today_sales.count(),
        'week_revenue': Payment.objects.filter(created_at__date__gte=week_start, status='PAID').aggregate(total=Sum('amount'))['total'] or 0,
        'month_revenue': Payment.objects.filter(created_at__date__gte=month_start, status='PAID').aggregate(total=Sum('amount'))['total'] or 0,
        'successful_payments': Payment.objects.filter(status='PAID').count(),
        'failed_payments': Payment.objects.filter(status='FAILED').count(),
        'pending_payments': Payment.objects.filter(status='PENDING').count(),
        'processing_payments': Payment.objects.filter(status='PROCESSING').count(),
        'recent_payments': Payment.objects.select_related('user', 'package').order_by('-created_at')[:10],
        'recent_customers': User.objects.filter(role='customer').order_by('-date_joined')[:5],
        'total_decoder_types': DecoderType.objects.count(),
        'total_packages': Package.objects.count(),
    }
    
    return render(request, 'business/dashboard.html', context)


# ============================================================================
# DECODER TYPES MANAGEMENT
# ============================================================================

@login_required
def decoder_types(request):
    """Business Owner - View and manage decoder types"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    all_decoder_types = DecoderType.objects.all().order_by('-created_at')
    
    context = {
        'decoder_types': all_decoder_types,
        'total_decoder_types': all_decoder_types.count(),
        'active_decoder_types': all_decoder_types.filter(is_active=True).count(),
    }
    
    return render(request, 'business/decoder_types.html', context)


@login_required
def add_decoder_type(request):
    """Business Owner - Add new decoder type"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip().upper()
    description = request.POST.get('description', '').strip()
    icon = request.POST.get('icon', 'bi-tv').strip()
    is_active = request.POST.get('is_active') == 'on'
    
    if not name:
        return JsonResponse({'error': 'Decoder name is required'}, status=400)
    if not code:
        return JsonResponse({'error': 'Decoder code is required'}, status=400)
    
    if DecoderType.objects.filter(name__iexact=name).exists():
        return JsonResponse({'error': 'Decoder name already exists'}, status=400)
    if DecoderType.objects.filter(code__iexact=code).exists():
        return JsonResponse({'error': 'Decoder code already exists'}, status=400)
    
    decoder_type = DecoderType.objects.create(
        name=name, code=code, description=description, icon=icon, is_active=is_active
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Decoder type "{decoder_type.name}" added successfully!',
        'decoder_type': {
            'id': decoder_type.id,
            'name': decoder_type.name,
            'code': decoder_type.code,
            'description': decoder_type.description,
            'icon': decoder_type.icon,
            'is_active': decoder_type.is_active,
        }
    })


@login_required
def edit_decoder_type(request, decoder_type_id):
    """Business Owner - Edit decoder type"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    decoder_type = get_object_or_404(DecoderType, id=decoder_type_id)
    
    if request.method != 'POST':
        # Return data for modal
        return JsonResponse({
            'id': decoder_type.id,
            'name': decoder_type.name,
            'code': decoder_type.code,
            'description': decoder_type.description,
            'icon': decoder_type.icon,
            'is_active': decoder_type.is_active,
        })
    
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip().upper()
    description = request.POST.get('description', '').strip()
    icon = request.POST.get('icon', 'bi-tv').strip()
    is_active = request.POST.get('is_active') == 'on'
    
    if not name:
        return JsonResponse({'error': 'Decoder name is required'}, status=400)
    if not code:
        return JsonResponse({'error': 'Decoder code is required'}, status=400)
    
    if DecoderType.objects.exclude(id=decoder_type.id).filter(name__iexact=name).exists():
        return JsonResponse({'error': 'Decoder name already exists'}, status=400)
    if DecoderType.objects.exclude(id=decoder_type.id).filter(code__iexact=code).exists():
        return JsonResponse({'error': 'Decoder code already exists'}, status=400)
    
    decoder_type.name = name
    decoder_type.code = code
    decoder_type.description = description
    decoder_type.icon = icon
    decoder_type.is_active = is_active
    decoder_type.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Decoder type "{decoder_type.name}" updated successfully!',
    })


@login_required
def delete_decoder_type(request, decoder_type_id):
    """Business Owner - Delete decoder type"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    decoder_type = get_object_or_404(DecoderType, id=decoder_type_id)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    if decoder_type.packages.exists():
        return JsonResponse({
            'error': f'Cannot delete "{decoder_type.name}". It has {decoder_type.packages.count()} package(s). Delete packages first.'
        }, status=400)
    
    decoder_name = decoder_type.name
    decoder_type.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'Decoder type "{decoder_name}" deleted successfully!'
    })


# ============================================================================
# PACKAGES MANAGEMENT
# ============================================================================

@login_required
def packages(request):
    """Business Owner - View and manage packages"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    decoder_types_list = DecoderType.objects.filter(is_active=True).order_by('name')
    all_packages = Package.objects.select_related('decoder_type').order_by('-created_at')
    
    # Filter by decoder type
    decoder_filter = request.GET.get('decoder')
    if decoder_filter:
        all_packages = all_packages.filter(decoder_type_id=decoder_filter)
    
    context = {
        'packages': all_packages,
        'total_packages': all_packages.count(),
        'active_packages': all_packages.filter(is_active=True).count(),
        'decoder_types': decoder_types_list,
        'decoder_filter': decoder_filter,
    }
    
    return render(request, 'business/packages.html', context)


@login_required
def add_package(request):
    """Business Owner - Add new package"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    decoder_type_id = request.POST.get('decoder_type', '').strip()
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    price = request.POST.get('price', '').strip()
    duration_months = request.POST.get('duration_months', '').strip()
    is_active = request.POST.get('is_active') == 'on'
    
    # Validate decoder type
    if not decoder_type_id:
        return JsonResponse({'error': 'Decoder type is required'}, status=400)
    
    try:
        decoder_type = DecoderType.objects.get(id=decoder_type_id)
    except DecoderType.DoesNotExist:
        return JsonResponse({'error': 'Invalid decoder type'}, status=400)
    
    # Validate name
    if not name:
        return JsonResponse({'error': 'Package name is required'}, status=400)
    
    if Package.objects.filter(decoder_type=decoder_type, name__iexact=name).exists():
        return JsonResponse({'error': f'Package "{name}" already exists for {decoder_type.name}'}, status=400)
    
    # Validate price
    try:
        price_value = float(price)
        if price_value <= 0:
            return JsonResponse({'error': 'Price must be greater than 0'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Valid price is required'}, status=400)
    
    # Validate duration
    try:
        duration = int(duration_months)
        if duration <= 0 or duration > 12:
            return JsonResponse({'error': 'Duration must be between 1 and 12 months'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Valid duration is required'}, status=400)
    
    package = Package.objects.create(
        decoder_type=decoder_type,
        name=name,
        description=description,
        price=price_value,
        duration_months=duration,
        is_active=is_active
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Package "{package.name}" added for {decoder_type.name}!',
        'package': {
            'id': package.id,
            'decoder_type': package.decoder_type.id,
            'decoder_type_name': package.decoder_type.name,
            'name': package.name,
            'price': str(package.price),
            'duration_months': package.duration_months,
            'is_active': package.is_active,
        }
    })


@login_required
def edit_package(request, package_id):
    """Business Owner - Edit package"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    package = get_object_or_404(Package, id=package_id)
    
    if request.method != 'POST':
        # Return data for modal
        return JsonResponse({
            'id': package.id,
            'decoder_type': package.decoder_type.id if package.decoder_type else None,
            'name': package.name,
            'description': package.description,
            'price': str(package.price),
            'duration_months': package.duration_months,
            'is_active': package.is_active,
        })
    
    decoder_type_id = request.POST.get('decoder_type', '').strip()
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    price = request.POST.get('price', '').strip()
    duration_months = request.POST.get('duration_months', '').strip()
    is_active = request.POST.get('is_active') == 'on'
    
    if not decoder_type_id:
        return JsonResponse({'error': 'Decoder type is required'}, status=400)
    
    try:
        decoder_type = DecoderType.objects.get(id=decoder_type_id)
    except DecoderType.DoesNotExist:
        return JsonResponse({'error': 'Invalid decoder type'}, status=400)
    
    if not name:
        return JsonResponse({'error': 'Package name is required'}, status=400)
    
    if Package.objects.filter(
        decoder_type=decoder_type, name__iexact=name
    ).exclude(id=package.id).exists():
        return JsonResponse({'error': f'Package "{name}" already exists for {decoder_type.name}'}, status=400)
    
    try:
        price_value = float(price)
        if price_value <= 0:
            return JsonResponse({'error': 'Price must be greater than 0'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Valid price is required'}, status=400)
    
    try:
        duration = int(duration_months)
        if duration <= 0 or duration > 12:
            return JsonResponse({'error': 'Duration must be between 1 and 12 months'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Valid duration is required'}, status=400)
    
    package.decoder_type = decoder_type
    package.name = name
    package.description = description
    package.price = price_value
    package.duration_months = duration
    package.is_active = is_active
    package.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Package "{package.name}" updated successfully!',
    })


@login_required
def delete_package(request, package_id):
    """Business Owner - Delete package"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    package = get_object_or_404(Package, id=package_id)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    payment_count = package.payments.count()
    if payment_count > 0:
        return JsonResponse({
            'error': f'Cannot delete "{package.name}". It has {payment_count} payment(s).'
        }, status=400)
    
    package_name = package.name
    decoder_name = package.decoder_type.name if package.decoder_type else "N/A"
    package.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'Package "{package_name}" from {decoder_name} deleted successfully!'
    })


# ============================================================================
# PAYMENTS MANAGEMENT
# ============================================================================

@login_required
def payments(request):
    """Business Owner - View all payments"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    payment_list = Payment.objects.select_related('user', 'package', 'decoder_type').order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        payment_list = payment_list.filter(status=status_filter)
    
    decoder_filter = request.GET.get('decoder')
    if decoder_filter:
        payment_list = payment_list.filter(decoder_type_id=decoder_filter)
    
    date_filter = request.GET.get('date')
    if date_filter:
        payment_list = payment_list.filter(created_at__date=date_filter)
    
    search_query = request.GET.get('search')
    if search_query:
        payment_list = payment_list.filter(
            Q(order_reference__icontains=search_query) |
            Q(decoder_number__icontains=search_query) |
            Q(user__phone_number__icontains=search_query)
        )
    
    paginator = Paginator(payment_list, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'decoder_filter': decoder_filter,
        'date_filter': date_filter,
        'search_query': search_query,
        'status_choices': Payment.STATUS_CHOICES,
        'decoder_types': DecoderType.objects.filter(is_active=True),
    }
    
    return render(request, 'business/payments.html', context)


@login_required
def payment_detail(request, payment_id):
    """Business Owner - View payment details"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Track viewed
    business = Business.objects.get(user=request.user)
    business_payment, created = BusinessPayment.objects.get_or_create(
        business=business, payment=payment
    )
    if not created:
        business_payment.viewed = True
        business_payment.viewed_at = timezone.now()
        business_payment.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'id': payment.id,
            'order_reference': payment.order_reference,
            'customer': payment.user.phone_number,
            'package': payment.package.name,
            'decoder_type': payment.decoder_type.name if payment.decoder_type else 'N/A',
            'decoder_number': payment.decoder_number,
            'total_decoders': payment.total_decoders,
            'total_months': payment.total_months,
            'amount': str(payment.amount),
            'payment_phone': payment.payment_phone,
            'transaction_id': payment.transaction_id,
            'status': payment.status,
            'status_display': payment.get_status_display(),
            'created_at': payment.created_at.strftime('%d %b %Y %H:%M'),
            'completed_at': payment.completed_at.strftime('%d %b %Y %H:%M') if payment.completed_at else None,
        })
    
    context = {'payment': payment}
    return render(request, 'business/payment_detail.html', context)


@login_required
def mark_payment_ready(request, payment_id):
    """Business Owner - Mark payment as READY (COMPLETED)"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if payment.status != 'PAID':
        return JsonResponse({
            'error': 'Payment must be PAID before marking as READY'
        }, status=400)
    
    payment.status = 'COMPLETED'
    payment.completed_at = timezone.now()
    payment.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Payment {payment.order_reference} marked as READY!',
        'status': payment.status
    })


# ============================================================================
# CUSTOMERS MANAGEMENT
# ============================================================================

@login_required
def customers(request):
    """Business Owner - View customers"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    customers_list = User.objects.filter(role='customer').order_by('-date_joined')
    
    search_query = request.GET.get('search')
    if search_query:
        customers_list = customers_list.filter(
            Q(phone_number__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(full_name__icontains=search_query)
        )
    
    paginator = Paginator(customers_list, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'total_customers': customers_list.count(),
        'active_customers': customers_list.filter(is_active=True).count(),
        'search_query': search_query,
    }
    
    return render(request, 'business/customers.html', context)


@login_required
def customer_detail(request, customer_id):
    """Business Owner - View customer details"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    customer = get_object_or_404(User, id=customer_id, role='customer')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'id': customer.id,
            'phone_number': customer.phone_number,
            'username': customer.username or 'N/A',
            'full_name': customer.full_name or 'N/A',
            'email': customer.email or 'N/A',
            'is_active': customer.is_active,
            'date_joined': customer.date_joined.strftime('%d %b %Y %H:%M'),
            'last_login': customer.last_login.strftime('%d %b %Y %H:%M') if customer.last_login else 'Never',
        })
    
    customer_payments = Payment.objects.filter(user=customer).order_by('-created_at')
    
    context = {
        'customer': customer,
        'customer_payments': customer_payments[:20],
        'total_spent': customer_payments.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0,
        'total_payments': customer_payments.count(),
        'successful_payments': customer_payments.filter(status='PAID').count(),
    }
    
    return render(request, 'business/customer_detail.html', context)


@login_required
def edit_customer(request, customer_id):
    """Business Owner - Edit customer"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    customer = get_object_or_404(User, id=customer_id, role='customer')
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    username = request.POST.get('username', '').strip()
    full_name = request.POST.get('full_name', '').strip()
    email = request.POST.get('email', '').strip()
    is_active = request.POST.get('is_active') == 'on'
    
    if not username:
        return JsonResponse({'error': 'Username is required'}, status=400)
    
    customer.username = username
    customer.full_name = full_name
    customer.email = email
    customer.is_active = is_active
    customer.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Customer {customer.phone_number} updated successfully!',
    })


@login_required
def deactivate_customer(request, customer_id):
    """Business Owner - Deactivate/Activate customer"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    customer = get_object_or_404(User, id=customer_id, role='customer')
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    action = request.POST.get('action', 'deactivate')
    
    if action == 'deactivate':
        customer.is_active = False
        customer.save()
        return JsonResponse({
            'success': True,
            'message': f'Customer {customer.phone_number} deactivated!',
            'is_active': False
        })
    elif action == 'activate':
        customer.is_active = True
        customer.save()
        return JsonResponse({
            'success': True,
            'message': f'Customer {customer.phone_number} activated!',
            'is_active': True
        })
    
    return JsonResponse({'error': 'Invalid action'}, status=400)


# ============================================================================
# SUBSCRIPTIONS
# ============================================================================

@login_required
def subscriptions(request):
    """Business Owner - Manage subscriptions"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    subscriptions_qs = Payment.objects.filter(
        status__in=['PAID', 'COMPLETED']
    ).select_related('user', 'package', 'decoder_type').order_by('-created_at')
    
    package_filter = request.GET.get('package')
    if package_filter:
        subscriptions_qs = subscriptions_qs.filter(package__id=package_filter)
    
    decoder_filter = request.GET.get('decoder')
    if decoder_filter:
        subscriptions_qs = subscriptions_qs.filter(decoder_type_id=decoder_filter)
    
    paginator = Paginator(subscriptions_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'packages': Package.objects.all(),
        'decoder_types': DecoderType.objects.filter(is_active=True),
        'package_filter': package_filter,
        'decoder_filter': decoder_filter,
        'total_subscriptions': subscriptions_qs.count(),
    }
    
    return render(request, 'business/subscriptions.html', context)


# ============================================================================
# REPORTS
# ============================================================================

@login_required
def reports(request):
    """Business Owner - View reports"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    from django.db.models.functions import TruncMonth, TruncDay
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    today = timezone.now().date()
    today_payments = Payment.objects.filter(created_at__date=today)
    
    # Revenue by decoder type
    revenue_by_decoder = Payment.objects.filter(status='PAID').values(
        'decoder_type__name'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    context = {
        'monthly_revenue': Payment.objects.filter(status='PAID').annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Sum('amount'), count=Count('id')
        ).order_by('-month'),
        
        'daily_revenue': Payment.objects.filter(
            status='PAID', created_at__gte=thirty_days_ago
        ).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            total=Sum('amount'), count=Count('id')
        ).order_by('day'),
        
        'status_breakdown': Payment.objects.values('status').annotate(count=Count('id')),
        'revenue_by_decoder': revenue_by_decoder,
        'total_revenue': Payment.objects.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0,
        'today_revenue': today_payments.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0,
        'today_payments_count': today_payments.count(),
        'top_customers': User.objects.filter(role='customer').annotate(
            total_spent=Sum('payments__amount', filter=Q(payments__status='PAID'))
        ).order_by('-total_spent')[:10],
    }
    
    return render(request, 'business/reports.html', context)


# ============================================================================
# BUSINESS SETTINGS
# ============================================================================

@login_required
def settings(request):
    """Business Owner - Business settings"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    business, created = Business.objects.get_or_create(
        user=request.user,
        defaults={
            'business_name': request.user.business_name or "My Business",
        }
    )
    
    if request.method == 'POST':
        business.business_name = request.POST.get('business_name', business.business_name)
        business.business_address = request.POST.get('business_address', business.business_address)
        business.business_phone = request.POST.get('business_phone', business.business_phone)
        business.business_email = request.POST.get('business_email', business.business_email)
        business.tax_id = request.POST.get('tax_id', business.tax_id)
        business.save()
        
        messages.success(request, "Business settings updated successfully!")
        return redirect('business_settings')
    
    context = {'business': business}
    return render(request, 'business/settings.html', context)