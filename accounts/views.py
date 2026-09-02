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