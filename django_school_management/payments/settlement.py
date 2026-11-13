from decimal import Decimal
from django.db import transaction
from django_school_management.students.models import AdmissionStudent
from .models import PaystackPayment


@transaction.atomic
def settle_paystack(data):
    if not isinstance(data, dict) or not isinstance(data.get('reference'), str):
        raise ValueError('Invalid payment data.')
    payment = PaystackPayment.objects.select_for_update().select_related('student__department_choice').get(transaction_reference=data['reference'])
    if (not payment.institute_id or not payment.student_id or
            payment.student.department_choice.institute_id != payment.institute_id):
        raise ValueError('Payment ownership does not match.')
    customer = data.get('customer')
    if (data.get('status') != 'success' or data.get('currency') != 'NGN' or
            type(data.get('amount')) is not int or payment.amount <= 0 or
            data['amount'] != int(payment.amount * Decimal(100)) or
            not isinstance(customer, dict) or
            str(customer.get('email', '')).casefold() != payment.payer_email.casefold()):
        raise ValueError('Payment details do not match.')
    if payment.status != 'success':
        payment.status = 'success'
        payment.paystack_response = {key: data[key] for key in ('id', 'reference', 'amount', 'currency', 'status', 'paid_at') if key in data}
        payment.save(update_fields=['status', 'paystack_response', 'modified'])
        AdmissionStudent.objects.filter(pk=payment.student_id).update(paid=True)
    return payment
