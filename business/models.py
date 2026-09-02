# business/models.py
from django.db import models
from django.conf import settings

class Business(models.Model):
    """Business profile - linked to User"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='business_profile')
    business_name = models.CharField(max_length=200)
    business_address = models.TextField(blank=True, null=True)
    business_phone = models.CharField(max_length=15, blank=True, null=True)
    business_email = models.EmailField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    # logo = models.ImageField(upload_to='business_logos/', blank=True, null=True)  # COMMENT OUT
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.business_name
    
    class Meta:
        verbose_name_plural = "Businesses"


class BusinessPayment(models.Model):
    """Business-specific payment tracking"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='payments')
    payment = models.ForeignKey('payments.Payment', on_delete=models.CASCADE)
    notes = models.TextField(blank=True, null=True)
    viewed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.business.business_name} - {self.payment.order_reference}"
    
    class Meta:
        ordering = ['-payment__created_at']