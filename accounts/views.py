# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import (
    RegisterForm,
    ProfileForm,
    CustomPasswordChangeForm,
)

from .utils import normalize_phone
from .models import User


def register_view(request):
    """User registration - Default role is Customer"""
    form = RegisterForm()

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            phone = normalize_phone(
                form.cleaned_data["phone_number"]
            )

            if not phone:
                messages.error(request, "Invalid phone number")
                return redirect("register")

            # Save user with default role 'customer'
            user = form.save(commit=False)
            user.phone_number = phone
            user.set_password(form.cleaned_data["password"])
            user.role = 'customer'  # Default role
            user.save()

            messages.success(request, "Account created successfully! Please login.")
            return redirect("login")

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    """Login with role-based redirect"""
    if request.method == "POST":
        phone = request.POST.get("phone_number")
        password = request.POST.get("password")

        phone1 = normalize_phone(phone)

        user = authenticate(
            request,
            username=phone1,
            password=password
        )

        if user:
            login(request, user)
            
            # ==========================================
            # ROLE-BASED REDIRECT - BILA NAMESPACE
            # ==========================================
            
            # Admin goes to Django admin
            if user.is_superuser or user.is_staff:
                return redirect("/admin/")  # ← Direct URL
            
            # Business Owner goes to business dashboard
            elif user.is_business_owner:
                return redirect("/business/")  # ← Direct URL
            
            # Customer goes to customer dashboard (packages)
            else:
                return redirect("/packages/")  # ← Direct URL

        messages.error(request, "Invalid credentials")

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    """User profile view with edit capability"""
    profile_form = ProfileForm(instance=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        # Update Profile
        if action == "update_profile":
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect("profile")

        # Change Password
        elif action == "change_password":
            password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Keep user logged in
                login(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect("profile")

    return render(request, "accounts/profile.html", {
        "profile_form": profile_form,
        "password_form": password_form,
    })


def welcome_view(request):
    """Welcome/Landing page"""
    return render(request, "accounts/welcome.html")


# accounts/views.py - Ongeza hizi views

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model

from .forms import (
    RegisterForm,
    ProfileForm,
    BusinessProfileForm,
    CustomPasswordChangeForm,
    ForgotPasswordForm,
    VerifyOTPForm,
    ResetPasswordForm,
)
from .models import PasswordResetOTP
from .services import send_password_reset_otp
from .utils import normalize_phone

User = get_user_model()


# ============================================================================
# FORGOT PASSWORD - Step 1: Enter phone
# ============================================================================

def forgot_password_view(request):
    """Step 1: Request password reset"""
    form = ForgotPasswordForm()
    
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        
        if form.is_valid():
            phone = form.cleaned_data['phone_number']
            user = User.objects.filter(phone_number=phone).first()
            
            if user:
                # Generate OTP
                otp = PasswordResetOTP.generate_otp(user, phone)
                
                # Send OTP via SMS
                sent = send_password_reset_otp(phone, otp.otp_code)
                
                if sent:
                    # Store user id in session
                    request.session['reset_user_id'] = user.id
                    request.session['reset_phone'] = phone
                    
                    messages.success(
                        request,
                        f"OTP sent to {phone}. Please check your SMS."
                    )
                    return redirect('verify_otp')
                else:
                    messages.error(request, "Failed to send SMS. Please try again.")
            else:
                messages.error(request, "No account found with this phone number")
    
    return render(request, 'accounts/forgot_password.html', {'form': form})


# ============================================================================
# FORGOT PASSWORD - Step 2: Verify OTP
# ============================================================================

def verify_otp_view(request):
    """Step 2: Verify OTP code"""
    user_id = request.session.get('reset_user_id')
    phone = request.session.get('reset_phone')
    
    if not user_id or not phone:
        messages.error(request, "Session expired. Please start again.")
        return redirect('forgot_password')
    
    form = VerifyOTPForm()
    
    if request.method == 'POST':
        form = VerifyOTPForm(request.POST)
        
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            
            # Find valid OTP
            otp = PasswordResetOTP.objects.filter(
                user_id=user_id,
                phone_number=phone,
                otp_code=otp_code,
                is_used=False,
                expires_at__gt=timezone.now()
            ).first()
            
            if otp:
                # Mark OTP as used
                otp.is_used = True
                otp.save()
                
                # Store in session for password reset
                request.session['otp_verified'] = True
                
                messages.success(request, "OTP verified! Set your new password.")
                return redirect('reset_password')
            else:
                messages.error(request, "Invalid or expired OTP. Please try again.")
    
    return render(request, 'accounts/verify_otp.html', {
        'form': form,
        'phone': phone,
    })


# ============================================================================
# FORGOT PASSWORD - Step 3: Reset Password
# ============================================================================

def reset_password_view(request):
    """Step 3: Set new password"""
    user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('otp_verified')
    
    if not user_id or not otp_verified:
        messages.error(request, "Session expired. Please start again.")
        return redirect('forgot_password')
    
    form = ResetPasswordForm()
    
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            
            # Update user password
            user = User.objects.filter(id=user_id).first()
            if user:
                user.set_password(new_password)
                user.save()
                
                # Clear session
                request.session.pop('reset_user_id', None)
                request.session.pop('reset_phone', None)
                request.session.pop('otp_verified', None)
                
                messages.success(
                    request,
                    "Password changed successfully! Please login."
                )
                return redirect('login')
            else:
                messages.error(request, "User not found")
    
    return render(request, 'accounts/reset_password.html', {'form': form})


# ============================================================================
# RESEND OTP
# ============================================================================

def resend_otp_view(request):
    """Resend OTP"""
    user_id = request.session.get('reset_user_id')
    phone = request.session.get('reset_phone')
    
    if not user_id or not phone:
        messages.error(request, "Session expired. Please start again.")
        return redirect('forgot_password')
    
    user = User.objects.filter(id=user_id).first()
    if not user:
        messages.error(request, "User not found")
        return redirect('forgot_password')
    
    # Generate new OTP
    otp = PasswordResetOTP.generate_otp(user, phone)
    
    # Send OTP
    sent = send_password_reset_otp(phone, otp.otp_code)
    
    if sent:
        messages.success(request, f"New OTP sent to {phone}")
    else:
        messages.error(request, "Failed to send SMS")
    
    return redirect('verify_otp')