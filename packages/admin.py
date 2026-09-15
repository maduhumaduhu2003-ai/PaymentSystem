from django.contrib import admin
from django.utils.html import format_html
from .models import DecoderType, Package


@admin.register(DecoderType)
class DecoderTypeAdmin(admin.ModelAdmin):
    
    list_display = (
        'name',
        'code',
        'icon_display',
        'package_count',
        'is_active',
        'created_at',
    )
    
    list_filter = (
        'is_active',
        'created_at',
    )
    
    search_fields = (
        'name',
        'code',
        'description',
    )
    
    ordering = ('name',)
    
    readonly_fields = (
        'created_at',
        'icon_display',
        'package_count',
    )
    
    fieldsets = (
        ('Decoder Information', {
            'fields': (
                'name',
                'code',
                'icon',
                'icon_display',
            )
        }),
        ('Description', {
            'fields': (
                'description',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                'created_at',
            )
        }),
    )
    
    def icon_display(self, obj):
        """Display icon preview"""
        return format_html(
            '<i class="{}" style="font-size: 24px; color: #f28c18;"></i>',
            obj.icon or 'bi bi-broadcast'
        )
    icon_display.short_description = 'Icon Preview'
    
    def package_count(self, obj):
        """Display package count"""
        count = obj.packages.count()
        return format_html(
            '<span style="background-color: #fff5e9; color: #f28c18; padding: 4px 10px; border-radius: 12px; font-size: 12px;">'
            '{} package{}</span>',
            count,
            's' if count != 1 else ''
        )
    package_count.short_description = 'Packages'


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    
    list_display = (
        'name',
        'decoder_type',
        'price_display',
        'duration_months',
        'is_active',
        'created_at',
    )
    
    list_filter = (
        'decoder_type',
        'is_active',
        'duration_months',
        'created_at',
    )
    
    search_fields = (
        'name',
        'description',
        'decoder_type__name',
    )
    
    ordering = ('decoder_type', 'price')
    
    readonly_fields = (
        'created_at',
        'price_display',
    )
    
    fieldsets = (
        ('Package Information', {
            'fields': (
                'decoder_type',
                'name',
                'description',
            )
        }),
        ('Pricing & Duration', {
            'fields': (
                'price',
                'price_display',
                'duration_months',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                'created_at',
            )
        }),
    )
    
    def price_display(self, obj):
        """Display price with TZS"""
        return format_html(
            '<strong style="color: #f28c18;">TZS {:,.2f}</strong>',
            obj.price
        )
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price'