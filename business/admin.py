from django.contrib import admin
from django.utils.html import format_html
from .models import Business, BusinessPayment


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    
    list_display = (
        'business_name',
        'user',
        'business_phone',
        'business_email',
        'tax_id',
        'created_at',
    )
    
    list_filter = (
        'created_at',
        'updated_at',
    )
    
    search_fields = (
        'business_name',
        'business_phone',
        'business_email',
        'tax_id',
        'user__phone_number',
        'user__username',
    )
    
    ordering = ('-created_at',)
    
    readonly_fields = (
        'created_at',
        'updated_at',
    )
    
    fieldsets = (
        ('Business Owner', {
            'fields': (
                'user',
            )
        }),
        ('Business Information', {
            'fields': (
                'business_name',
                'business_address',
                'business_phone',
                'business_email',
                'tax_id',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(BusinessPayment)
class BusinessPaymentAdmin(admin.ModelAdmin):
    
    list_display = (
        'id',
        'business',
        'payment',
        'viewed',
        'viewed_at',
    )
    
    list_filter = (
        'viewed',
        'payment__status',
        'viewed_at',
    )
    
    search_fields = (
        'business__business_name',
        'payment__order_reference',
        'payment__user__phone_number',
    )
    
    ordering = ('-payment__created_at',)
    
    readonly_fields = (
        'business',
        'payment',
        'viewed_at',
    )
    
    fieldsets = (
        ('Business Payment', {
            'fields': (
                'business',
                'payment',
                'notes',
            )
        }),
        ('Tracking', {
            'fields': (
                'viewed',
                'viewed_at',
            )
        }),
    )