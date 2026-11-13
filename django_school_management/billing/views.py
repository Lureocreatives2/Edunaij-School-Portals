import stripe
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .services import StripeWebhookService
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error("Invalid payload")
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature")
        return HttpResponseBadRequest("Invalid signature")

    # Pass the event to our service
    StripeWebhookService.handle_event(event)

    return HttpResponse(status=200)


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseForbidden
from .models import Subscription, Invoice


@login_required
def billing_dashboard(request):
    tenant = getattr(request, 'tenant', None)
    if (not tenant or not request.user.is_staff or
            (not request.user.is_superuser and request.user.tenant_id != tenant.pk)):
        return HttpResponseForbidden('School billing administrator access is required.')
    return render(request, 'billing/dashboard.html', {
        'tenant': tenant,
        'subscription': Subscription.objects.filter(tenant=tenant).first(),
        'invoices': Invoice.objects.filter(tenant=tenant).order_by('-created_at')[:50],
    })
