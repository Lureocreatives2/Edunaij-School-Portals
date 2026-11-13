from django_school_management.payments.access import payment_applicant
from django_school_management.tenants.scoping import request_institute
from django.http import HttpResponse
import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse

from django_school_management.students.models import AdmissionStudent
from django_school_management.students.tasks import send_admission_confirmation_email

logger = logging.getLogger(__name__)


def online_admission_stripepayment(request, pk):
    payment_applicant(request, pk)
    return HttpResponse('This payment method is unavailable while provider verification is being completed. Please contact the school.', status=503)



def stripe_payment_success(request, pk):
    registrant = payment_applicant(request, pk)
    return HttpResponse('Payment is awaiting provider verification. Please contact the school if it remains pending.', status=202)


def stripe_payment_cancel(request, pk):
    registrant = payment_applicant(request, pk)
    return render(request, 'pages/students/admission_payment_cancel.html', {
        'registrant': registrant,
    })
