from django_school_management.payments.access import payment_applicant
from django_school_management.tenants.scoping import request_institute
from django.http import HttpResponse
import logging

from sslcommerz_lib import SSLCOMMERZ
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from django_school_management.students.models import AdmissionStudent
from django_school_management.payments.models import SSLPayment

logger = logging.getLogger(__name__)

ssl_settings = {
    'store_id': settings.STORE_ID,
    'store_pass': settings.STORE_PASS,
    'issandbox': settings.SSL_ISSANDBOX,
}


def _store_admission_pay_record(post_body, institute):
    try:
        SSLPayment.objects.create(
            institute=institute,
            transaction_id=post_body['tran_id'],
            payer=post_body['cus_name'],
            received_amount=post_body['total_amount'],
            pay_reason=SSLPayment.SSL_PAY_REASONS[0][0],
            payer_mobile=post_body['cus_phone'],
            payer_email=post_body['cus_email'],
            payer_city=post_body['cus_city'],
            payer_country=post_body['cus_country'],
        )
        return True
    except Exception:
        logger.exception("Failed to store SSL payment record")
        return False


def online_admission_sslpayment(request, pk):
    payment_applicant(request, pk)
    return HttpResponse('This payment method is unavailable while provider verification is being completed. Please contact the school.', status=503)



@csrf_exempt
def ssl_payment_success(request, pk):
    """SSLCommerz redirects here after successful payment."""
    registrant = payment_applicant(request, pk)
    return HttpResponse('Payment is awaiting provider verification. Please contact the school if it remains pending.', status=202)


@csrf_exempt
def ssl_payment_fail(request, pk):
    """SSLCommerz redirects here after a failed payment."""
    messages.error(request, "Payment failed. Please try again or contact support.")
    return redirect('pages:online_admission_sslpayment', pk=pk)


@csrf_exempt
def ssl_payment_cancel(request, pk):
    """SSLCommerz redirects here when the user cancels."""
    messages.warning(request, "Payment was cancelled.")
    return redirect('pages:online_admission')
