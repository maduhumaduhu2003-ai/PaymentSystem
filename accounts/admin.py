from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    
    # =========================================================================
    # LIST DISPLAY
    # =========================================================================
    
    list_display = (
        'phone_number',
        'username',
        'role_badge',
        'business_name',
        'is_active',
        'is_staff',
        'date_joined',
    )
    
    list_filter = (
        'role',
        'is_active',
        'is_staff',
        'is_superuser',
        'date_joined',
    )
    
    search_fields = (
        'phone_number',
        'username',
        'business_name',
        'email',
        'full_name',
    )
    
    ordering = ('-date_joined',)
    
    # =========================================================================
    # FIELDSETS (Detail View)
    # =========================================================================
    
    fieldsets = (
        ('Authentication', {
            'fields': (
                'phone_number',
                'password',
            )
        }),
        ('Personal Information', {
            'fields': (
                'username',
                'full_name',
                'email',
                'first_name',
                'last_name',
            )
        }),
        ('Role & Business', {
            'fields': (
                'role',
                'business_name',
                'business_address',
                'business_phone',
                'business_email',
                'tax_id',
            )
        }),
        ('Location', {
            'fields': (
                'address',
                'city',
            ),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
        ('Important Dates', {
            'fields': (
                'last_login',
                'date_joined',
            )
        }),
    )
    
    # =========================================================================
    # ADD FIELDSETS (Create User)
    # =========================================================================
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'phone_number',
                'username',
                'role',
                'business_name',
                'business_address',
                'password1',
                'password2',
            ),
        }),
    )
    
    # =========================================================================
    # READONLY
    # =========================================================================
    
    readonly_fields = (
        'last_login',
        'date_joined',
        'role_badge',
    )
    
    # =========================================================================
    # CUSTOM DISPLAY METHODS
    # =========================================================================
    
    def role_badge(self, obj):
        """Display role with colored badge"""
        colors = {
            'admin': ('#dc3545', '#ffffff'),
            'business_owner': ('#f28c18', '#ffffff'),
            'customer': ('#17a2b8', '#ffffff'),
        }
        bg, color = colors.get(obj.role, ('#6c757d', '#ffffff'))
        
        icons = {
            'admin': 'fa-shield-alt',
            'business_owner': 'fa-building',
            'customer': 'fa-user',
        }
        icon = icons.get(obj.role, 'fa-user')
        
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;">'
            '<i class="fas {}"></i> {}</span>',
            bg, color, icon, obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    
    # =========================================================================
    # CUSTOM FORM
    # =========================================================================
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'phone_number' in form.base_fields:
            form.base_fields['phone_number'].required = True
        return form
    
    # =========================================================================
    # ADMIN ACTIONS
    # =========================================================================
    
    actions = [
        'make_customer',
        'make_business_owner',
        'activate_users',
        'deactivate_users',
    ]
    
    def make_customer(self, request, queryset):
        updated = queryset.update(role='customer')
        self.message_user(request, f"{updated} user(s) changed to Customer")
    make_customer.short_description = "👤 Make Customer"
    
    def make_business_owner(self, request, queryset):
        updated = queryset.update(role='business_owner')
        self.message_user(request, f"{updated} user(s) changed to Business Owner")
    make_business_owner.short_description = "🏢 Make Business Owner"
    
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated")
    activate_users.short_description = "✅ Activate users"
    
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated")
    deactivate_users.short_description = "❌ Deactivate users"