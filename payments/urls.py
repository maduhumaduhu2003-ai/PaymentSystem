from django.urls import path
from .views import (
    admin_dashboard,
    make_payment,
    payments_list,
    payment_status,
    transactions,
    mark_completed,
    start_processing,
)
from payments import views

urlpatterns = [
    path('pay/<int:package_id>/', make_payment, name='make_payment'),
    path('status/<int:payment_id>/', payment_status, name='payment_status'),
   
    path('list/', payments_list, name='payments_list'),
    path('transactions/', transactions, name='transactions'),
    path('callback/', views.clickpesa_callback, name='clickpesa_callback'),
    path('admin/payments/', admin_dashboard, name='admin_dashboard'),
    path('admin/process/<int:payment_id>/', start_processing, name='start_processing'),
    path('admin/complete/<int:payment_id>/', mark_completed, name='mark_completed'),
    path('retry/<int:payment_id>/', views.retry_payment, name='retry_payment'),
]