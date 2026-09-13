# subscriptions/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone


class DecoderSubscription(models.Model):
    """Track each decoder subscription separately"""
    
    STATUS_ACTIVE = "ACTIVE"
    STATUS_EXPIRED = "EXPIRED"
    STATUS_CANCELLED = "CANCELLED"
    
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="decoder_subscriptions"
    )
    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    payment_item = models.OneToOneField(
        'payments.PaymentItem',
        on_delete=models.CASCADE,
        related_name="subscription",
        null=True,
        blank=True
    )
    decoder_number = models.CharField(max_length=100, db_index=True)
    package = models.ForeignKey(
        'packages.Package',
        on_delete=models.PROTECT
    )
    decoder_type = models.ForeignKey(
        'packages.DecoderType',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    months = models.IntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['decoder_number', 'status']),
            models.Index(fields=['expires_at', 'status']),
        ]
    
    def __str__(self):
        return f"{self.decoder_number} - {self.package.name}"
    
    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE and self.expires_at > timezone.now()
    
    @property
    def days_remaining(self):
        if self.expires_at > timezone.now():
            return (self.expires_at - timezone.now()).days
        return 0