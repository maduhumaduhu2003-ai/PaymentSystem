from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta

from packages.models import Package
from payments.models import Payment
from .models import Business, BusinessPayment
from accounts.models import User  # ← IMPORTANT: HII NDIO ILIKOSA


# ============================================================================
# BUSINESS DASHBOARD - View sales
# ============================================================================

@login_required
def dashboard(request):
    """Business Owner Dashboard - View sales"""
    
    if not request.user.is_business_owner:
        messages.error(request, "Access denied. Business owners only.")
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
        'recent_payments': Payment.objects.all().order_by('-created_at')[:10],
        'recent_customers': User.objects.filter(role='customer').order_by('-date_joined')[:5],  # ← Sasa inafanya kazi
    }
    
    return render(request, 'business/dashboard.html', context)


# ============================================================================
# BUSINESS PAYMENTS - View payments
# ============================================================================

@login_required
def payments(request):
    """Business Owner - View all payments"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    payment_list = Payment.objects.all().order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        payment_list = payment_list.filter(status=status_filter)
    
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
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'search_query': search_query,
        'status_choices': Payment.STATUS_CHOICES,
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
        business=business,
        payment=payment
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
            'decoder_number': payment.decoder_number,
            'amount': str(payment.amount),
            'payment_phone': payment.payment_phone,
            'transaction_id': payment.transaction_id,
            'status': payment.status,
            'status_display': payment.get_status_display(),
            'created_at': payment.created_at.strftime('%d %b %Y %H:%M'),
            'completed_at': payment.completed_at.strftime('%d %b %Y %H:%M') if payment.completed_at else None,
            'processed_at': payment.processed_at.strftime('%d %b %Y %H:%M') if payment.processed_at else None,
        })
    
    context = {'payment': payment}
    return render(request, 'business/payment_detail.html', context)


@login_required
def mark_payment_ready(request, payment_id):
    """Business Owner - Mark payment as READY"""
    
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
# BUSINESS CUSTOMERS - View customers
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
            Q(username__icontains=search_query)
        )
    
    paginator = Paginator(customers_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_customers': customers_list.count(),
        'active_customers': customers_list.filter(is_active=True).count(),
        'search_query': search_query,
    }
    
    return render(request, 'business/customers.html', context)


# ============================================================================
# BUSINESS CUSTOMER DETAIL (HTML & JSON)
# ============================================================================

@login_required
def customer_detail(request, customer_id):
    """Business Owner - View customer details (HTML or JSON)"""
    
    if not request.user.is_business_owner:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Access denied'}, status=403)
        return HttpResponseForbidden("Access denied")
    
    customer = get_object_or_404(User, id=customer_id, role='customer')
    
    # Kama ni AJAX request, rudi JSON (kwa modal)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'id': customer.id,
            'phone_number': customer.phone_number,
            'username': customer.username or 'N/A',
            'email': customer.email or 'N/A',
            'is_active': customer.is_active,
            'date_joined': customer.date_joined.strftime('%d %b %Y %H:%M'),
            'last_login': customer.last_login.strftime('%d %b %Y %H:%M') if customer.last_login else 'Never',
            'role': customer.role,
        })
    
    # Kama ni HTML request, rudi page
    customer_payments = Payment.objects.filter(user=customer).order_by('-created_at')
    
    context = {
        'customer': customer,
        'customer_payments': customer_payments[:20],
        'total_spent': customer_payments.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0,
        'total_payments': customer_payments.count(),
        'successful_payments': customer_payments.filter(status='PAID').count(),
    }
    
    return render(request, 'business/customer_detail.html', context)


# ============================================================================
# BUSINESS EDIT CUSTOMER
# ============================================================================

@login_required
def edit_customer(request, customer_id):
    """Business Owner - Edit customer via modal"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    customer = get_object_or_404(User, id=customer_id, role='customer')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        if not username:
            return JsonResponse({'error': 'Username is required'}, status=400)
        
        customer.username = username
        customer.email = email
        customer.is_active = is_active
        customer.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Customer {customer.phone_number} updated successfully!',
            'customer': {
                'id': customer.id,
                'phone_number': customer.phone_number,
                'username': customer.username,
                'email': customer.email,
                'is_active': customer.is_active,
            }
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


# ============================================================================
# BUSINESS DEACTIVATE/ACTIVATE CUSTOMER
# ============================================================================

@login_required
def deactivate_customer(request, customer_id):
    """Business Owner - Deactivate or activate customer"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    customer = get_object_or_404(User, id=customer_id, role='customer')
    
    if request.method == 'POST':
        action = request.POST.get('action', 'deactivate')
        
        if action == 'deactivate':
            customer.is_active = False
            customer.save()
            return JsonResponse({
                'success': True,
                'message': f'Customer {customer.phone_number} deactivated successfully!',
                'is_active': False
            })
        elif action == 'activate':
            customer.is_active = True
            customer.save()
            return JsonResponse({
                'success': True,
                'message': f'Customer {customer.phone_number} activated successfully!',
                'is_active': True
            })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


# ============================================================================
# BUSINESS PACKAGES - Manage packages
# ============================================================================

@login_required
def packages(request):
    """Business Owner - View and manage packages"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    all_packages = Package.objects.all().order_by('-created_at')
    
    context = {
        'packages': all_packages,
        'total_packages': all_packages.count(),
        'active_packages': all_packages.filter(is_active=True).count(),
    }
    
    return render(request, 'business/packages.html', context)


@login_required
def add_package(request):
    """Business Owner - Add new package via modal"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '').strip()
        duration_months = request.POST.get('duration_months', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        if not name:
            return JsonResponse({'error': 'Package name is required'}, status=400)
        
        try:
            price_value = float(price)
            if price_value <= 0:
                return JsonResponse({'error': 'Price must be greater than 0'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Valid price is required'}, status=400)
        
        try:
            duration = int(duration_months)
            if duration <= 0:
                return JsonResponse({'error': 'Duration must be at least 1 month'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Valid duration is required'}, status=400)
        
        package = Package.objects.create(
            name=name,
            description=description,
            price=price_value,
            duration_months=duration,
            is_active=is_active
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Package added successfully!',
            'package': {
                'id': package.id,
                'name': package.name,
                'description': package.description,
                'price': str(package.price),
                'duration_months': package.duration_months,
                'is_active': package.is_active,
            }
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def edit_package(request, package_id):
    """Business Owner - Edit package via modal"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    package = get_object_or_404(Package, id=package_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '').strip()
        duration_months = request.POST.get('duration_months', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        if not name:
            return JsonResponse({'error': 'Package name is required'}, status=400)
        
        try:
            price_value = float(price)
            if price_value <= 0:
                return JsonResponse({'error': 'Price must be greater than 0'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Valid price is required'}, status=400)
        
        try:
            duration = int(duration_months)
            if duration <= 0:
                return JsonResponse({'error': 'Duration must be at least 1 month'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Valid duration is required'}, status=400)
        
        package.name = name
        package.description = description
        package.price = price_value
        package.duration_months = duration
        package.is_active = is_active
        package.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Package updated successfully!',
            'package': {
                'id': package.id,
                'name': package.name,
                'description': package.description,
                'price': str(package.price),
                'duration_months': package.duration_months,
                'is_active': package.is_active,
            }
        })
    
    return JsonResponse({
        'id': package.id,
        'name': package.name,
        'description': package.description,
        'price': str(package.price),
        'duration_months': package.duration_months,
        'is_active': package.is_active,
    })


@login_required
def delete_package(request, package_id):
    """Business Owner - Delete package via modal"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    package = get_object_or_404(Package, id=package_id)
    
    if request.method == 'POST':
        package_name = package.name
        package.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Package "{package_name}" deleted successfully!'
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


# ============================================================================
# BUSINESS SUBSCRIPTIONS - Manage subscriptions
# ============================================================================

@login_required
def subscriptions(request):
    """Business Owner - Manage subscriptions"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    subscriptions = Payment.objects.filter(
        status__in=['PAID', 'COMPLETED']
    ).order_by('-created_at')
    
    package_filter = request.GET.get('package')
    if package_filter:
        subscriptions = subscriptions.filter(package__id=package_filter)
    
    paginator = Paginator(subscriptions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'packages': Package.objects.all(),
        'package_filter': package_filter,
        'total_subscriptions': subscriptions.count(),
    }
    
    return render(request, 'business/subscriptions.html', context)


# ============================================================================
# BUSINESS REPORTS
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
    
    context = {
        'monthly_revenue': Payment.objects.filter(status='PAID').annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-month'),
        
        'daily_revenue': Payment.objects.filter(
            status='PAID',
            created_at__gte=thirty_days_ago
        ).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('day'),
        
        'status_breakdown': Payment.objects.values('status').annotate(count=Count('id')),
        'total_revenue': Payment.objects.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0,
        'today_revenue': today_payments.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0,
        'today_payments_count': today_payments.count(),
        'top_customers': User.objects.filter(role='customer').annotate(  # ← Sasa inafanya kazi
            total_spent=Sum('payment__amount', filter=Q(payment__status='PAID'))
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