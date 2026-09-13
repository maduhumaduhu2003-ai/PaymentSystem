from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import timedelta

from .models import DecoderSubscription
from payments.models import Payment


# ============================================================================
# CUSTOMER: MY SUBSCRIPTIONS
# ============================================================================

@login_required
def my_subscriptions(request):
    """Customer - View their subscriptions"""
    
    subscriptions = DecoderSubscription.objects.filter(
        user=request.user
    ).select_related('package', 'decoder_type', 'payment').order_by('-started_at')
    
    # Stats
    now = timezone.now()
    active_count = subscriptions.filter(
        status='ACTIVE',
        expires_at__gt=now
    ).count()
    expired_count = subscriptions.filter(
        Q(status='EXPIRED') | Q(expires_at__lte=now)
    ).count()
    total_count = subscriptions.count()
    
    # Pagination
    paginator = Paginator(subscriptions, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'active_count': active_count,
        'expired_count': expired_count,
        'total_count': total_count,
        'now': now,
    }
    
    return render(request, 'subscriptions/my_subscriptions.html', context)


# ============================================================================
# CUSTOMER: SUBSCRIPTION DETAIL
# ============================================================================

@login_required
def subscription_detail(request, subscription_id):
    """Customer - View subscription details"""
    
    subscription = get_object_or_404(
        DecoderSubscription,
        id=subscription_id,
        user=request.user
    )
    
    return render(request, 'subscriptions/subscription_detail.html', {
        'subscription': subscription
    })


# ============================================================================
# BUSINESS: ALL SUBSCRIPTIONS
# ============================================================================

@login_required
def business_subscriptions(request):
    """Business Owner - View all subscriptions"""
    
    if not request.user.is_business_owner:
        return HttpResponseForbidden("Access denied")
    
    subscriptions = DecoderSubscription.objects.select_related(
        'user', 'package', 'decoder_type', 'payment'
    ).order_by('-started_at')
    
    # Filters
    status_filter = request.GET.get('status')
    if status_filter:
        subscriptions = subscriptions.filter(status=status_filter)
    
    decoder_filter = request.GET.get('decoder')
    if decoder_filter:
        subscriptions = subscriptions.filter(decoder_type_id=decoder_filter)
    
    search_query = request.GET.get('search')
    if search_query:
        subscriptions = subscriptions.filter(
            Q(decoder_number__icontains=search_query) |
            Q(user__phone_number__icontains=search_query)
        )
    
    # Stats
    now = timezone.now()
    active_count = DecoderSubscription.objects.filter(
        status='ACTIVE', expires_at__gt=now
    ).count()
    expired_count = DecoderSubscription.objects.filter(
        Q(status='EXPIRED') | Q(expires_at__lte=now)
    ).count()
    
    # Pagination
    paginator = Paginator(subscriptions, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    from packages.models import DecoderType
    
    context = {
        'page_obj': page_obj,
        'active_count': active_count,
        'expired_count': expired_count,
        'total_count': DecoderSubscription.objects.count(),
        'status_filter': status_filter,
        'decoder_filter': decoder_filter,
        'search_query': search_query,
        'decoder_types': DecoderType.objects.filter(is_active=True),
        'now': now,
    }
    
    return render(request, 'business/subscriptions.html', context)


# ============================================================================
# BUSINESS: SUBSCRIPTION ACTION (Activate/Expire)
# ============================================================================

@login_required
def update_subscription_status(request, subscription_id):
    """Business Owner - Update subscription status"""
    
    if not request.user.is_business_owner:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    subscription = get_object_or_404(DecoderSubscription, id=subscription_id)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    action = request.POST.get('action', '').strip()
    
    if action == 'activate':
        subscription.status = 'ACTIVE'
        subscription.activated_at = timezone.now()
        subscription.save()
        return JsonResponse({
            'success': True,
            'message': f'Subscription {subscription.decoder_number} activated!',
            'status': subscription.status,
        })
    
    elif action == 'expire':
        subscription.status = 'EXPIRED'
        subscription.save()
        return JsonResponse({
            'success': True,
            'message': f'Subscription {subscription.decoder_number} expired!',
            'status': subscription.status,
        })
    
    elif action == 'cancel':
        subscription.status = 'CANCELLED'
        subscription.cancelled_at = timezone.now()
        subscription.save()
        return JsonResponse({
            'success': True,
            'message': f'Subscription {subscription.decoder_number} cancelled!',
            'status': subscription.status,
        })
    
    return JsonResponse({'error': 'Invalid action'}, status=400)