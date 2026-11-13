
from .views import InitiatePaystackPaymentView, paystack_webhook, verify_paystack_payment
from django.urls import path
from . import views


app_name = 'payments'

urlpatterns = [
    path('sslpays/', views.dashboard_ssl_payments_list, 
        name='dashboard_ssl_payments_list'
    ),

    path('paystack/initiate/', InitiatePaystackPaymentView.as_view(), name='paystack_initiate'),
    path('paystack/webhook/', paystack_webhook, name='paystack_webhook'),
    path('paystack/verify/<str:reference>/', verify_paystack_payment, name='paystack_verify'),
]