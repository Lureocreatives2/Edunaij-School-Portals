from django.contrib import admin
from .models import StripeCustomer, Subscription, Invoice, UsageRecord

@admin.register(StripeCustomer)
class StripeCustomerAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'stripe_customer_id', 'email_for_payments', 'created_at')
    search_fields = ('tenant__name', 'stripe_customer_id', 'email_for_payments')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'status', 'current_period_end', 'auto_renew', 'updated_at')
    list_filter = ('status', 'auto_renew')
    search_fields = ('tenant__name', 'stripe_subscription_id')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'stripe_invoice_id', 'amount', 'currency', 'status', 'due_date')
    list_filter = ('status', 'currency')
    search_fields = ('stripe_invoice_id', 'tenant__name')

@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'metric', 'count', 'period_start', 'period_end')
    list_filter = ('metric',)
    search_fields = ('tenant__name',)
