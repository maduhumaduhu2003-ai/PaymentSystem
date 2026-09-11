# packages/admin.py

from django.contrib import admin
from .models import DecoderType, Package


@admin.register(DecoderType)
class DecoderTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'decoder_type', 'price', 'duration_months', 'is_active')
    list_filter = ('decoder_type', 'is_active')
    search_fields = ('name',)