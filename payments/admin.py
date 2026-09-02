from django.contrib import admin
from .models import Payment
from django.utils import timezone


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'package',
        'amount',
        'payment_phone',
        'status',
        'transaction_id',
        'created_at'
    )

    list_filter = (
        'status',
        'package',
        'created_at'
    )

    search_fields = (
        'payment_phone',
        'transaction_id',
        'decoder_number',
        'user__phone_number'
    )

    ordering = ('-created_at',)

    readonly_fields = (
        'transaction_id',
        'order_reference',
        'created_at'
    )

    actions = ['mark_as_processing', 'mark_as_completed']

    # -----------------------------
    # ADMIN ACTION: PROCESS
    # -----------------------------
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status='PROCESSING')
        self.message_user(request, f"{updated} payment(s) moved to PROCESSING")

    mark_as_processing.short_description = "Mark selected as Processing"


    # -----------------------------
    # ADMIN ACTION: COMPLETE
    # -----------------------------
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(
            status='COMPLETED',
            completed_at=timezone.now()
        )
        self.message_user(request, f"{updated} payment(s) marked COMPLETED")

    mark_as_completed.short_description = "Mark selected as Completed"