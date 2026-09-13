from django.contrib import admin
from .models import DecoderSubscription


@admin.register(DecoderSubscription)
class DecoderSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('decoder_number', 'user', 'package', 'months', 'status', 'expires_at')
    list_filter = ('status', 'decoder_type', 'package')
    search_fields = ('decoder_number', 'user__phone_number')
    ordering = ('-started_at',)
    readonly_fields = ('started_at', 'activated_at')