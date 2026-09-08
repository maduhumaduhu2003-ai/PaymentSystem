from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinLengthValidator


class User(AbstractUser):
    # Roles
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('business_owner', 'Business Owner'),
        ('customer', 'Customer'),
    )
    
    LANGUAGE_CHOICES = (
        ('sw', 'Swahili'),
        ('en', 'English'),
    )
    
    # Core fields
    username = models.CharField(max_length=150, blank=True, null=True)
    phone_number = models.CharField(max_length=15, unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer', db_index=True)
    
    # Business Owner fields
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)
    business_phone = models.CharField(max_length=15, blank=True, null=True)
    business_email = models.EmailField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="TIN Number")
    
    # Customer fields
    full_name = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    # Preferences
    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='sw')
    notifications_enabled = models.BooleanField(default=True)
    
    # Verification
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']

    class Meta:
        indexes = [
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['phone_number', 'role']),
        ]
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.phone_number} - {self.get_role_display()}"
    
    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
    
    @property
    def is_business_owner(self):
        return self.role == 'business_owner'
    
    @property
    def is_customer(self):
        return self.role == 'customer'
    
    @property
    def display_name(self):
        """Get the best display name for the user"""
        if self.full_name:
            return self.full_name
        if self.business_name:
            return self.business_name
        if self.username:
            return self.username
        return self.phone_number
    
    @property
    def is_onboarded(self):
        """Check if user has completed onboarding"""
        if self.is_customer:
            return bool(self.phone_number and (self.full_name or self.username))
        if self.is_business_owner:
            return bool(
                self.phone_number and 
                self.business_name and 
                self.business_address
            )
        return True