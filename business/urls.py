# business/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='business_dashboard'),
    path('dashboard/', views.dashboard, name='business_dashboard'),
    
    # Payments
    path('payments/', views.payments, name='business_payments'),
    path('payment/<int:payment_id>/', views.payment_detail, name='business_payment_detail'),
    path('payment/mark-ready/<int:payment_id>/', views.mark_payment_ready, name='business_mark_ready'),
    
    # Customers
    path('customers/', views.customers, name='business_customers'),
    path('customer/<int:customer_id>/', views.customer_detail, name='business_customer_detail'),
    path('customer/<int:customer_id>/', views.customer_detail_json, name='business_customer_json'),
    path('customer/edit/<int:customer_id>/', views.edit_customer, name='business_edit_customer'),
    path('customer/deactivate/<int:customer_id>/', views.deactivate_customer, name='business_deactivate_customer'),
    
    # Packages - Manage
    path('packages/', views.packages, name='business_packages'),
    path('packages/add/', views.add_package, name='business_add_package'),
    path('packages/edit/<int:package_id>/', views.edit_package, name='business_edit_package'),
    path('packages/delete/<int:package_id>/', views.delete_package, name='business_delete_package'),
    
    # Subscriptions
    path('subscriptions/', views.subscriptions, name='business_subscriptions'),
    
    # Reports
    path('reports/', views.reports, name='business_reports'),
    
    # Settings
    path('settings/', views.settings, name='business_settings'),
]