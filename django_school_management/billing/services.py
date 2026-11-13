import stripe
from django.conf import settings
from django.utils import timezone
from django_school_management.billing.models import StripeCustomer, Subscription, Invoice
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

class StripeWebhookService:
    
    @classmethod
    def handle_event(cls, event):
        """Route the Stripe event to the correct handler."""
        handler_map = {
            'payment_intent.succeeded': cls.handle_payment_success,
            'payment_intent.payment_failed': cls.handle_payment_failed,
            'customer.subscription.updated': cls.handle_subscription_updated,
            'customer.subscription.deleted': cls.handle_subscription_deleted,
            'invoice.payment_succeeded': cls.handle_invoice_paid,
            'invoice.payment_failed': cls.handle_invoice_failed,
        }
        
        handler = handler_map.get(event.type)
        if handler:
            try:
                handler(event.data.object)
                logger.info(f"Successfully handled Stripe event: {event.type}")
            except Exception as e:
                logger.error(f"Error handling {event.type}: {e}")
        else:
            logger.warning(f"Unhandled Stripe event type: {event.type}")

    @classmethod
    def handle_payment_success(cls, payment_intent):
        # Logic for successful payment intent
        pass

    @classmethod
    def handle_payment_failed(cls, payment_intent):
        # Logic for failed payment intent
        pass

    @classmethod
    def handle_subscription_updated(cls, subscription):
        try:
            # Find our local subscription via Stripe ID
            sub = Subscription.objects.get(stripe_subscription_id=subscription.id)
            sub.status = subscription.status
            sub.current_period_start = timezone.datetime.fromtimestamp(subscription.current_period_start)
            sub.current_period_end = timezone.datetime.fromtimestamp(subscription.current_period_end)
            sub.save()
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription not found for Stripe ID: {subscription.id}")

    @classmethod
    def handle_subscription_deleted(cls, subscription):
        try:
            sub = Subscription.objects.get(stripe_subscription_id=subscription.id)
            sub.status = 'canceled'
            sub.save()
        except Subscription.DoesNotExist:
            pass

    @classmethod
    def handle_invoice_paid(cls, invoice):
        try:
            inv = Invoice.objects.get(stripe_invoice_id=invoice.id)
            inv.status = 'paid'
            inv.paid_at = timezone.now()
            inv.save()
        except Invoice.DoesNotExist:
            pass

    @classmethod
    def handle_invoice_failed(cls, invoice):
        try:
            inv = Invoice.objects.get(stripe_invoice_id=invoice.id)
            inv.status = 'open' # or 'past_due' depending on your logic
            inv.save()
        except Invoice.DoesNotExist:
            pass
