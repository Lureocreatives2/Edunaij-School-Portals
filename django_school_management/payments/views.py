from django_school_management.tenants.scoping import request_institute, require_school_staff
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
from django.views.generic import ListView
from .models import SSLPayment
from .tables import SSLPaymentTable
from .filters import SSLPaymentFilter


class DashboardSSLPaymentsList(SingleTableMixin, FilterView):
    model = SSLPayment
    table_class = SSLPaymentTable
    template_name = 'payments/dashboard/sslpayments.html'
    filterset_class = SSLPaymentFilter

    def get_queryset(self):
        require_school_staff(self.request)
        return super().get_queryset().filter(institute=request_institute(self.request))

dashboard_ssl_payments_list = DashboardSSLPaymentsList.as_view()

# ==========================================
# PAYSTACK VIEWS
# ==========================================
import uuid
import json
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.contrib import messages
from .models import PaystackPayment
from .utils.paystack_service import PaystackService

from django.views.decorators.http import require_POST
from decimal import Decimal
from .access import payment_applicant
from .settlement import settle_paystack


class InitiatePaystackPaymentView(View):
    def post(self, request, *args, **kwargs):
        student_id = request.POST.get('student_id')
        if not student_id or not student_id.isdigit():
            return JsonResponse({'error': 'A valid application is required.'}, status=400)
        student = payment_applicant(request, student_id)
        institute = request_institute(request)
        amount = institute.admission_fee
        if amount is None or amount <= 0:
            return JsonResponse({'error': 'The school has not configured an admission fee.'}, status=409)
        reference = 'SCH-' + uuid.uuid4().hex
        txn = PaystackPayment.objects.create(student=student, institute=institute,
            transaction_reference=reference, amount=amount, payer_email=student.email,
            payer_name=student.name)
        response = PaystackService.initialize_transaction(email=txn.payer_email,
            amount=txn.amount, reference=reference,
            metadata={'student_id': student.pk, 'institute_id': institute.pk})
        if response.get('status') is True:
            return redirect(response['data']['authorization_url'])
        txn.status = 'failed'
        txn.save(update_fields=['status', 'modified'])
        return JsonResponse({'error': 'Payment could not be initialized. Please try again.'}, status=502)


@csrf_exempt
@require_POST
def paystack_webhook(request):
    if not PaystackService.verify_webhook_signature(request.body,
            request.headers.get('x-paystack-signature', ''),
            request.headers.get('Paystack-Signature')):
        return HttpResponse(status=401)
    try:
        event = json.loads(request.body)
        if not isinstance(event, dict):
            raise ValueError('Invalid event.')
        if event.get('event') == 'charge.success':
            settle_paystack(event.get('data'))
    except PaystackPayment.DoesNotExist:
        return HttpResponse(status=200)
    except (ValueError, TypeError, UnicodeDecodeError):
        return HttpResponse(status=400)
    return HttpResponse(status=200)


@require_POST
def verify_paystack_payment(request, reference):
    txn = get_object_or_404(PaystackPayment, transaction_reference=reference,
        institute=request_institute(request))
    payment_applicant(request, txn.student_id)
    response = PaystackService.verify_transaction(reference)
    data = response.get('data')
    if response.get('status') is not True or not isinstance(data, dict) or data.get('reference') != reference:
        return JsonResponse({'status': 'failed'}, status=400)
    try:
        settle_paystack(data)
    except (ValueError, PaystackPayment.DoesNotExist):
        return JsonResponse({'status': 'failed'}, status=400)
    return JsonResponse({'status': 'success'})
