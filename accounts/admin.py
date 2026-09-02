from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    # Fields to display in list view
    list_display = ('phone_number', 'username', 'role', 'business_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('phone_number', 'username', 'business_name', 'email')
    ordering = ('-date_joined',)
    
    # Fields to display in detail view
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal Info', {'fields': ('username', 'email', 'first_name', 'last_name')}),
        ('Business Info', {'fields': ('role', 'business_name', 'business_address')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Fields for creating new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'username', 'role', 'business_name', 'business_address', 'password1', 'password2'),
        }),
    )
    
    # Make phone number required
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['phone_number'].required = True
        return form

# Register User model
admin.site.register(User, UserAdmin)