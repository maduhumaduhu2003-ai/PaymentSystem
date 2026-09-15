from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Payment, PaymentItem


# ============================================================================
# PAYMENT ITEM INLINE (Kwa kuonyesha items ndani ya payment)
# ============================================================================

class PaymentItemInline(admin.TabularInline):
    model = PaymentItem
    extra = 0
    readonly_fields = ('decoder_number', 'months', 'unit_price', 'subtotal', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# PAYMENT ADMIN
# ============================================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    
    # =========================================================================
    # LIST DISPLAY
    # =========================================================================
    
    list_display = (
        'id',
        'order_reference',
        'user',
        'package',
        'decoder_type',
        'total_decoders',
        'total_months',
        'amount_display',
        'payment_method_display',
        'status_badge',
        'created_at',
    )
    
    list_filter = (
        'status',
        'payment_method',
        'decoder_type',
        'package',
        'created_at',
    )
    
    search_fields = (
        'order_reference',
        'transaction_id',
        'payment_phone',
        'decoder_number',
        'user__phone_number',
        'user__username',
    )
    
    ordering = ('-created_at',)
    
    date_hierarchy = 'created_at'
    
    # =========================================================================
    # READONLY FIELDS
    # =========================================================================
    
    readonly_fields = (
        'order_reference',
        'transaction_id',
        'payment_url',
        'gateway_status',
        'gateway_message',
        'webhook_received_at',
        'webhook_processed',
        'last_checked_at',
        'requires_review',
        'review_reason',
        'created_at',
        'processed_at',
        'paid_at',
        'completed_at',
        'amount_display',
        'payment_method_display',
        'status_badge',
    )
    
    # =========================================================================
    # FIELDSETS (Detail View)
    # =========================================================================
    
    fieldsets = (
        ('Customer Information', {
            'fields': (
                'user',
                'payment_phone',
            )
        }),
        ('Package Information', {
            'fields': (
                'package',
                'decoder_type',
                'decoder_number',
                'total_decoders',
                'total_months',
            )
        }),
        ('Payment Details', {
            'fields': (
                'amount',
                'currency',
                'payment_method',
                'payment_method_display',
                'status',
                'status_badge',
            )
        }),
        ('Gateway Information', {
            'fields': (
                'order_reference',
                'transaction_id',
                'payment_url',
                'gateway_status',
                'gateway_message',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'processed_at',
                'paid_at',
                'completed_at',
                'last_checked_at',
            ),
            'classes': ('collapse',)
        }),
        ('Webhook & Review', {
            'fields': (
                'webhook_received_at',
                'webhook_processed',
                'requires_review',
                'review_reason',
            ),
            'classes': ('collapse',)
        }),
    )
    
    # =========================================================================
    # INLINES
    # =========================================================================
    
    inlines = [PaymentItemInline]
    
    # =========================================================================
    # CUSTOM DISPLAY METHODS
    # =========================================================================
    
    def amount_display(self, obj):
        """Display amount with TZS currency"""
        return format_html(
            '<strong style="color: #f28c18;">TZS {:,.2f}</strong>',
            obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def payment_method_display(self, obj):
        """Display payment method with icon"""
        icons = {
            'USSD': '<i class="fas fa-mobile-alt"></i> USSD',
            'CARD': '<i class="fas fa-credit-card"></i> Card',
            'MOBILE': '<i class="fas fa-mobile"></i> Mobile',
        }
        return format_html(
            icons.get(obj.payment_method, obj.payment_method)
        )
    payment_method_display.short_description = 'Method'
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'PENDING': ('#ffc107', '#856404'),
            'PROCESSING': ('#007bff', '#ffffff'),
            'PAID': ('#17a2b8', '#ffffff'),
            'COMPLETED': ('#28a745', '#ffffff'),
            'FAILED': ('#dc3545', '#ffffff'),
            'REVIEW': ('#ffc107', '#856404'),
        }
        bg, color = colors.get(obj.status, ('#6c757d', '#ffffff'))
        
        icons = {
            'PENDING': 'fa-hourglass-half',
            'PROCESSING': 'fa-spinner',
            'PAID': 'fa-check-circle',
            'COMPLETED': 'fa-check-double',
            'FAILED': 'fa-times-circle',
            'REVIEW': 'fa-exclamation-triangle',
        }
        icon = icons.get(obj.status, 'fa-circle')
        
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;">'
            '<i class="fas {}"></i> {}</span>',
            bg, color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    # =========================================================================
    # ADMIN ACTIONS
    # =========================================================================
    
    actions = [
        'mark_as_processing',
        'mark_as_paid',
        'mark_as_completed',
        'mark_as_failed',
        'mark_as_review',
    ]
    
    def mark_as_processing(self, request, queryset):
        updated = 0
        for payment in queryset:
            if payment.mark_processing():
                payment.save()
                updated += 1
        self.message_user(request, f"{updated} payment(s) moved to PROCESSING")
    mark_as_processing.short_description = "✅ Mark as Processing"
    
    def mark_as_paid(self, request, queryset):
        updated = 0
        for payment in queryset:
            if payment.mark_paid():
                payment.save()
                updated += 1
        self.message_user(request, f"{updated} payment(s) marked as PAID")
    mark_as_paid.short_description = "💰 Mark as Paid"
    
    def mark_as_completed(self, request, queryset):
        updated = 0
        for payment in queryset:
            if payment.mark_completed():
                payment.save()
                updated += 1
        self.message_user(request, f"{updated} payment(s) marked as COMPLETED")
    mark_as_completed.short_description = "✅ Mark as Completed"
    
    def mark_as_failed(self, request, queryset):
        updated = 0
        for payment in queryset:
            if payment.mark_failed():
                payment.save()
                updated += 1
        self.message_user(request, f"{updated} payment(s) marked as FAILED")
    mark_as_failed.short_description = "❌ Mark as Failed"
    
    def mark_as_review(self, request, queryset):
        updated = 0
        for payment in queryset:
            if payment.mark_review("Marked by admin"):
                payment.save()
                updated += 1
        self.message_user(request, f"{updated} payment(s) marked as REVIEW")
    mark_as_review.short_description = "⚠️ Mark as Review"


# ============================================================================
# PAYMENT ITEM ADMIN
# ============================================================================

@admin.register(PaymentItem)
class PaymentItemAdmin(admin.ModelAdmin):
    
    list_display = (
        'id',
        'payment',
        'decoder_number',
        'months',
        'unit_price',
        'subtotal',
        'created_at',
    )
    
    list_filter = (
        'months',
        'created_at',
    )
    
    search_fields = (
        'decoder_number',
        'payment__order_reference',
        'payment__user__phone_number',
    )
    
    ordering = ('-created_at',)
    
    readonly_fields = (
        'payment',
        'package',
        'decoder_number',
        'months',
        'unit_price',
        'subtotal',
        'created_at',
    )