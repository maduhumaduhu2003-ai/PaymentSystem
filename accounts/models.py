# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Roles
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('business_owner', 'Business Owner'),
        ('customer', 'Customer'),
    )
    
    username = models.CharField(max_length=150, blank=True, null=True)
    phone_number = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    
    # Business Owner fields
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.phone_number} - {self.get_role_display()}"
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_business_owner(self):
        return self.role == 'business_owner'
    
    @property
    def is_customer(self):
        return self.role == 'customer'