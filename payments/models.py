from decimal import Decimal
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.validators import MinValueValidator
from accounts.models import User
from packages.models import Package


class Payment(models.Model):
    # Status constants
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVIEW = "REVIEW"

    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (PROCESSING, "Processing"),
        (PAID, "Paid"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (REVIEW, "Requires Review"),
    )

    VALID_TRANSITIONS = {
        PENDING: [PROCESSING, FAILED, REVIEW],
        PROCESSING: [PAID, FAILED, REVIEW],
        PAID: [COMPLETED, REVIEW],
        COMPLETED: [],
        FAILED: [],
        REVIEW: [PAID, FAILED],
    }

    # Fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments", db_index=True)
    package = models.ForeignKey(Package, on_delete=models.PROTECT, related_name="payments", db_index=True)

    decoder_number = models.CharField(max_length=100)
    payment_phone = models.CharField(max_length=15, db_index=True)

    transaction_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    order_reference = models.CharField(max_length=100, unique=True)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3, default="TZS")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Webhook tracking
    webhook_received_at = models.DateTimeField(null=True, blank=True)
    webhook_processed = models.BooleanField(default=False)

    # Review/Reconciliation
    requires_review = models.BooleanField(default=False, db_index=True)
    review_reason = models.CharField(max_length=255, blank=True, default="")
    gateway_status = models.CharField(max_length=50, blank=True, default="")
    gateway_message = models.CharField(max_length=500, blank=True, default="")
    last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"], name="pay_user_status_idx"),
            models.Index(fields=["package", "status"], name="pay_package_status_idx"),
            models.Index(fields=["created_at", "status"], name="pay_created_status_idx"),
            models.Index(fields=["requires_review", "status"], name="pay_review_status_idx"),
        ]
        constraints = [
            # Use strings directly instead of Payment.PENDING
            models.UniqueConstraint(
                fields=["user", "package"],
                condition=Q(status__in=["PENDING", "PROCESSING"]),
                name="unique_active_payment_per_user_package",
            ),
        ]

    def __str__(self):
        return f"{self.order_reference} - {self.status}"

    def can_transition_to(self, new_status):
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status):
        if not self.can_transition_to(new_status):
            return False
        self.status = new_status
        return True

    def mark_processing(self):
        if self.transition_to(self.PROCESSING):
            self.processed_at = self.processed_at or timezone.now()
            return True
        return False

    def mark_paid(self):
        if self.transition_to(self.PAID):
            self.paid_at = self.paid_at or timezone.now()
            return True
        return False

    def mark_completed(self):
        if self.transition_to(self.COMPLETED):
            self.completed_at = self.completed_at or timezone.now()
            return True
        return False

    def mark_failed(self):
        if self.transition_to(self.FAILED):
            self.processed_at = self.processed_at or timezone.now()
            return True
        return False

    def mark_review(self, reason=""):
        if self.transition_to(self.REVIEW):
            self.requires_review = True
            self.review_reason = reason[:255]
            return True
        return False

    @property
    def is_final(self):
        return self.status in (self.COMPLETED, self.FAILED)

    @property
    def is_active(self):
        return self.status in (self.PENDING, self.PROCESSING)