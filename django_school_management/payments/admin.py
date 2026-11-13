from .models import PaystackPayment
from django.contrib import admin
from .models import SSLPayment, SSLAdmissionPaymentVerfication


@admin.register(SSLPayment)
class SSLPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id',
        'payer',
        'received_amount',
        'pay_reason',
        'payer_mobile',
        'payer_email'
    )


@admin.register(SSLAdmissionPaymentVerfication)
class SSLAdmissionPaymentVerficationAdmin(admin.ModelAdmin):
    list_display = (
        'payment',
        'status',
        'verified_by',
    )


@admin.register(PaystackPayment)
class PaystackPaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_reference', 'student', 'institute', 'amount', 'status', 'created')
    list_filter = ('status', 'institute', 'created')
    search_fields = ('transaction_reference', 'payer_email', 'payer_name')
    readonly_fields = ('transaction_reference', 'amount', 'paystack_response', 'created', 'modified')
