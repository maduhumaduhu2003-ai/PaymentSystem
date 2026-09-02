from django.contrib import admin
from .models import Package


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'duration_months',
        'price',
        'is_active',
        'created_at'
    )

    list_filter = (
        'is_active',
        'duration_months'
    )

    search_fields = (
        'name',
    )

    ordering = ('price',)

    list_editable = ('price', 'is_active')

    readonly_fields = ('created_at',)