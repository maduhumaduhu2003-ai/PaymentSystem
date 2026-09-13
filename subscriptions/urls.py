from django.urls import path
from . import views

urlpatterns = [
    # Customer
    path('my/', views.my_subscriptions, name='my_subscriptions'),
    path('detail/<int:subscription_id>/', views.subscription_detail, name='subscription_detail'),
    
    # Business
    path('business/', views.business_subscriptions, name='business_subscriptions'),
    path('business/update/<int:subscription_id>/', views.update_subscription_status, name='update_subscription_status'),
]