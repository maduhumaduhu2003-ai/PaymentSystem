from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import DecoderSubscription


@admin.register(DecoderSubscription)
class DecoderSubscriptionAdmin(admin.ModelAdmin):
    
    # =========================================================================
    # LIST DISPLAY
    # =========================================================================
    
    list_display = (
        'id',
        'decoder_number',
        'user',
        'package',
        'decoder_type',
        'months',
        'status_badge',
        'days_remaining_display',
        'expires_at',
        'started_at',
    )
    
    list_filter = (
        'status',
        'decoder_type',
        'package',
        'started_at',
        'expires_at',
    )
    
    search_fields = (
        'decoder_number',
        'user__phone_number',
        'user__username',
        'package__name',
        'payment__order_reference',
    )
    
    ordering = ('-started_at',)
    
    date_hierarchy = 'started_at'
    
    # =========================================================================
    # READONLY FIELDS
    # =========================================================================
    
    readonly_fields = (
        'started_at',
        'activated_at',
        'cancelled_at',
        'status_badge',
        'days_remaining_display',
        'is_active_display',
    )
    
    # =========================================================================
    # FIELDSETS
    # =========================================================================
    
    fieldsets = (
        ('Customer & Payment', {
            'fields': (
                'user',
                'payment',
                'payment_item',
            )
        }),
        ('Subscription Details', {
            'fields': (
                'decoder_number',
                'package',
                'decoder_type',
                'months',
            )
        }),
        ('Status & Dates', {
            'fields': (
                'status',
                'status_badge',
                'is_active_display',
                'days_remaining_display',
                'started_at',
                'activated_at',
                'expires_at',
                'cancelled_at',
            )
        }),
    )
    
    # =========================================================================
    # CUSTOM DISPLAY METHODS
    # =========================================================================
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'ACTIVE': ('#28a745', '#ffffff', 'fa-check-circle'),
            'EXPIRED': ('#dc3545', '#ffffff', 'fa-times-circle'),
            'CANCELLED': ('#6c757d', '#ffffff', 'fa-ban'),
        }
        bg, color, icon = colors.get(obj.status, ('#6c757d', '#ffffff', 'fa-circle'))
        
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;">'
            '<i class="fas {}"></i> {}</span>',
            bg, color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def days_remaining_display(self, obj):
        """Display days remaining with color"""
        days = obj.days_remaining
        
        if obj.status == 'CANCELLED':
            return format_html('<span style="color: #6c757d;">Cancelled</span>')
        
        if days <= 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: 600;">Expired</span>'
            )
        elif days <= 7:
            return format_html(
                '<span style="color: #ffc107; font-weight: 600;">{} days</span>',
                days
            )
        else:
            return format_html(
                '<span style="color: #28a745; font-weight: 600;">{} days</span>',
                days
            )
    days_remaining_display.short_description = 'Days Remaining'
    
    def is_active_display(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-weight: 600;">'
                '<i class="fas fa-check-circle"></i> Active</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: 600;">'
            '<i class="fas fa-times-circle"></i> Not Active</span>'
        )
    is_active_display.short_description = 'Is Active'
    
    # =========================================================================
    # ADMIN ACTIONS
    # =========================================================================
    
    actions = [
        'mark_as_active',
        'mark_as_expired',
        'mark_as_cancelled',
        'extend_30_days',
        'extend_90_days',
    ]
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f"{updated} subscription(s) marked as ACTIVE")
    mark_as_active.short_description = "✅ Mark as Active"
    
    def mark_as_expired(self, request, queryset):
        updated = queryset.update(status='EXPIRED')
        self.message_user(request, f"{updated} subscription(s) marked as EXPIRED")
    mark_as_expired.short_description = "⏰ Mark as Expired"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(
            status='CANCELLED',
            cancelled_at=timezone.now()
        )
        self.message_user(request, f"{updated} subscription(s) marked as CANCELLED")
    mark_as_cancelled.short_description = "❌ Mark as Cancelled"
    
    def extend_30_days(self, request, queryset):
        from datetime import timedelta
        updated = 0
        for sub in queryset:
            sub.expires_at = sub.expires_at + timedelta(days=30)
            sub.save()
            updated += 1
        self.message_user(request, f"{updated} subscription(s) extended by 30 days")
    extend_30_days.short_description = "📅 Extend 30 days"
    
    def extend_90_days(self, request, queryset):
        from datetime import timedelta
        updated = 0
        for sub in queryset:
            sub.expires_at = sub.expires_at + timedelta(days=90)
            sub.save()
            updated += 1
        self.message_user(request, f"{updated} subscription(s) extended by 90 days")
    extend_90_days.short_description = "📅 Extend 90 days"