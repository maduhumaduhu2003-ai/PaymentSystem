from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import User
from .utils import normalize_phone, validate_tanzania_phone


class RegisterForm(forms.ModelForm):
    """Registration form - Default role is Customer"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'id': 'passwordInput',
            'placeholder': 'Enter password (min 8 characters)',
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'id': 'confirmPasswordInput',
            'placeholder': 'Confirm password',
        })
    )

    class Meta:
        model = User
        fields = ['phone_number', 'username', 'password', 'confirm_password']
        
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '07XXXXXXXX or 2557XXXXXXXX',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username',
            }),
        }

    def clean_phone_number(self):
        """Validate phone number is unique and valid"""
        phone = self.cleaned_data.get('phone_number')
        
        if not validate_tanzania_phone(phone):
            raise forms.ValidationError("Invalid Tanzania phone number. Use 07XXXXXXXX or 2557XXXXXXXX")
        
        normalized = normalize_phone(phone)
        if not normalized:
            raise forms.ValidationError("Invalid phone number format")
        
        if User.objects.filter(phone_number=normalized).exists():
            raise forms.ValidationError("Phone number already registered")
        
        return normalized

    def clean(self):
        """Validate passwords match"""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password and confirm and password != confirm:
            self.add_error('confirm_password', "Passwords do not match")
        
        if password and len(password) < 8:
            self.add_error('password', "Password must be at least 8 characters")

        return cleaned_data

    def save(self, commit=True):
        """Save user with default role as Customer"""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = 'customer'
        
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Profile update form for customers"""
    
    class Meta:
        model = User
        fields = ['full_name', 'username', 'phone_number', 'email', 'address', 'city']
        
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full name',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number',
                'readonly': True,  # Phone number cannot be changed
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter address',
                'rows': 2,
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter city',
            }),
        }

    def clean_phone_number(self):
        """Phone number should not be changed"""
        phone = self.cleaned_data.get('phone_number')
        if phone != self.instance.phone_number:
            raise forms.ValidationError("Phone number cannot be changed. Contact support.")
        return phone


class BusinessProfileForm(forms.ModelForm):
    """Profile update form for business owners"""
    
    class Meta:
        model = User
        fields = [
            'business_name', 'business_address', 'business_phone',
            'business_email', 'tax_id', 'full_name', 'email'
        ]
        
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter business name',
            }),
            'business_address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter business address',
                'rows': 3,
            }),
            'business_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter business phone',
            }),
            'business_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter business email',
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter TIN number',
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact person name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact email',
            }),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    """Password change form with custom styling"""
    
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter current password",
        })
    )

    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter new password (min 8 characters)",
        })
    )

    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm new password",
        })
    )
    
    def clean_new_password1(self):
        """Validate password strength"""
        password = self.cleaned_data.get('new_password1')
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters")
        return password