from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import User


class RegisterForm(forms.ModelForm):
    """Registration form - Default role is Customer"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'id': 'passwordInput',
            'placeholder': 'Enter password',
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
        """Validate phone number is unique"""
        phone = self.cleaned_data.get('phone_number')
        if User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("Phone number already registered")
        return phone

    def clean(self):
        """Validate passwords match"""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password and confirm and password != confirm:
            self.add_error('confirm_password', "Passwords do not match")

        return cleaned_data

    def save(self, commit=True):
        """Save user with default role as Customer"""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        
        # Default role is Customer
        user.role = 'customer'
        
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Profile update form"""
    
    class Meta:
        model = User
        fields = ["username", "phone_number"]
        
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter username",
            }),
            "phone_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter phone number",
                "readonly": True,
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