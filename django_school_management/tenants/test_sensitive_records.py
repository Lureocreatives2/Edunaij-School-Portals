import hashlib
import hmac
import json
import time
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from . import test_isolation as isolation
from django_school_management.payments.models import PaystackPayment
from django_school_management.payments.views import paystack_webhook, verify_paystack_payment, InitiatePaystackPaymentView
from django_school_management.payments.utils.paystack_service import PaystackService
from django_school_management.students.models import Student
from django_school_management.academics.models import Semester, AcademicSession, Batch
from django_school_management.result.views import find_student, result_detail_view
from django_school_management.students.views.report_views import yearly_graph_api
from django_school_management.utils.private_media import school_media


@override_settings(PAYSTACK_SECRET_KEY='sk_test_fixture', PAYSTACK_WEBHOOK_SECRET='whsec_fixture')
class SensitiveRecordTests(TestCase):
    setUpTestData = isolation.TwoSchoolIsolationTests.__dict__['setUpTestData']

    def setUp(self):
        self.school_a.admission_fee = Decimal('100.00')
        self.school_a.save(update_fields=['admission_fee'])
        self.payment = PaystackPayment.objects.create(institute=self.school_a, student=self.app_a,
            transaction_reference='test-payment', amount=100, payer_email='payer@example.test')

    def request(self, method='get', data=None, user=None):
        request = getattr(RequestFactory(), method)('/', data or {})
        request.user = user or self.user
        request.tenant = self.alpha
        request.session = {}
        return request

    def event(self, **changes):
        data = {'reference': self.payment.transaction_reference, 'amount': 10000, 'currency': 'NGN',
            'status': 'success', 'customer': {'email': self.payment.payer_email}}
        data.update(changes)
        return {'event': 'charge.success', 'data': data}

    def webhook(self, event, valid=True):
        body = json.dumps(event).encode()
        signature = hmac.new(b'sk_test_fixture', body, hashlib.sha512).hexdigest() if valid else 'invalid'
        request = RequestFactory().post('/', body, content_type='application/json', HTTP_X_PAYSTACK_SIGNATURE=signature)
        return paystack_webhook(request)

    def test_valid_signed_payment_settles_once(self):
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        self.payment.refresh_from_db()
        modified = self.payment.modified
        self.assertEqual(self.payment.status, 'success')
        self.app_a.refresh_from_db()
        self.assertTrue(self.app_a.paid)
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.modified, modified)

    def test_invalid_signature_cannot_settle(self):
        self.assertEqual(self.webhook(self.event(), valid=False).status_code, 401)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    def test_wrong_amount_currency_and_customer_are_rejected(self):
        for changes in ({'amount': 1}, {'currency': 'USD'}, {'customer': {'email': 'other@example.test'}}, {'amount': '10000'}):
            self.assertEqual(self.webhook(self.event(**changes)).status_code, 400)
        self.payment.refresh_from_db()
        self.app_a.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')
        self.assertFalse(self.app_a.paid)

    def test_timestamped_signatures_reject_expired_and_downgrade(self):
        body = b'{}'
        timestamp = str(int(time.time()))
        digest = hmac.new(b'whsec_fixture', timestamp.encode()+b'.'+body, hashlib.sha512).hexdigest()
        self.assertTrue(PaystackService.verify_webhook_signature(body, '', f't={timestamp},v1=whk_test:{digest}'))
        self.assertFalse(PaystackService.verify_webhook_signature(body, '', f't=1,v1=whk_test:{digest}'))
        legacy = hmac.new(b'sk_test_fixture', body, hashlib.sha512).hexdigest()
        self.assertFalse(PaystackService.verify_webhook_signature(body, legacy, 'invalid'))

    @patch.object(PaystackService, 'initialize_transaction', return_value={'status': True, 'data': {'authorization_url': 'https://checkout.paystack.com/test'}})
    def test_checkout_ignores_client_price(self, initialize):
        response = InitiatePaystackPaymentView.as_view()(self.request('post', {'student_id': str(self.app_a.pk), 'amount': '0.01'}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(initialize.call_args.kwargs['amount'], Decimal('100.00'))

    def test_anonymous_checkout_requires_application_session(self):
        request = self.request('post', {'student_id': str(self.app_a.pk)}, AnonymousUser())
        with self.assertRaises(PermissionDenied):
            InitiatePaystackPaymentView.as_view()(request)

    def test_other_school_payment_is_hidden(self):
        other = PaystackPayment.objects.create(institute=self.school_b, student=self.app_b, transaction_reference='beta', amount=100)
        with self.assertRaises(Http404):
            verify_paystack_payment(self.request('post'), other.transaction_reference)

    def test_legacy_browser_returns_cannot_mark_application_paid(self):
        from django_school_management.pages.payment_views.stripe_pay import stripe_payment_success
        from django_school_management.pages.payment_views.sslpay import ssl_payment_success
        for view in (stripe_payment_success, ssl_payment_success):
            self.assertEqual(view(self.request(), self.app_a.pk).status_code, 202)
        self.app_a.refresh_from_db()
        self.assertFalse(self.app_a.paid)

    def test_reports_count_only_current_school(self):
        response = yearly_graph_api(self.request())
        data = json.loads(response.content)['data']
        self.assertEqual(sum(row['count'] for row in data['applications']), 1)

    def test_anonymous_report_is_denied(self):
        with self.assertRaises(PermissionDenied):
            yearly_graph_api(self.request(user=AnonymousUser()))

    def test_result_lookup_cannot_find_other_school_student(self):
        semester = Semester.objects.create(number=1)
        session = AcademicSession.objects.create(year=2026)
        batch = Batch.objects.create(year=session, number=1, department=self.dept_b)
        student = Student.objects.bulk_create([Student(admission_student=self.app_b, semester=semester, batch=batch, temporary_id='beta-child')])[0]
        with self.assertRaises(Http404):
            find_student(self.request(), student.temporary_id)
        with self.assertRaises(Http404):
            result_detail_view.__wrapped__(self.request(), student.pk)

    def test_private_student_media_requires_owner_and_school(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            self.app_a.photo.save('child.jpg', SimpleUploadedFile('child.jpg', b'private image'))
            name = self.app_a.photo.name
            anonymous = self.request(user=AnonymousUser())
            with self.assertRaises(Http404):
                school_media(anonymous, name)
            anonymous.session['admission_applicants'] = [str(self.app_a.pk)]
            response = school_media(anonymous, name)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            response.close()
            self.app_b.photo.name = name
            self.app_b.save()
            foreign = self.request()
            foreign.tenant = self.beta
            foreign.user = AnonymousUser()
            with self.assertRaises(Http404):
                school_media(foreign, name)

    def test_unreferenced_and_traversal_media_are_hidden(self):
        for name in ('../db.sqlite3', 'students/unknown.jpg'):
            with self.assertRaises(Http404):
                school_media(self.request(), name)

    def test_result_filter_queryset_and_choices_are_school_scoped(self):
        from django_school_management.result.views import result_view
        from django.http import HttpResponse
        req = self.request(data={'semester': '1'})
        with patch('django_school_management.result.views.render', return_value=HttpResponse()) as render:
            result_view.__wrapped__(req)
        filterset = render.call_args.args[2]['filter']
        choices = filterset.filters['student__admission_student__choosen_department'].queryset
        self.assertEqual(list(choices), [self.dept_a])
        self.assertIn('institute_id', str(filterset.qs.query))

    def test_editor_fields_use_plain_text_widgets(self):
        from django.forms import Textarea
        from django_school_management.articles.forms import ArticleForm
        from django_school_management.notices.models import Notice
        self.assertEqual(type(ArticleForm().fields['content'].widget), Textarea)
        self.assertEqual(type(Notice._meta.get_field('content').formfield().widget), Textarea)

    def test_ckeditor_upload_route_has_been_removed(self):
        from django.urls import resolve, Resolver404
        with self.assertRaises(Resolver404):
            resolve('/ckeditor/upload/')

    def test_media_route_uses_authorized_view(self):
        from django.urls import resolve
        self.assertEqual(resolve('/media/students/applicant/photo.jpg').func, school_media)

    def test_malformed_signature_is_rejected_without_error(self):
        self.assertFalse(PaystackService.verify_webhook_signature(b'{}', chr(233)))
        timestamp = str(int(time.time()))
        self.assertFalse(PaystackService.verify_webhook_signature(b'{}', '', f't={timestamp},v1=whk_test:{chr(233)}'))

    def test_legacy_braintree_cannot_charge_or_mark_paid(self):
        from django_school_management.pages.views import online_admission_payment, payment
        for view in (online_admission_payment, payment):
            self.assertEqual(view(self.request('post'), self.app_a.pk).status_code, 503)
        self.app_a.refresh_from_db()
        self.assertFalse(self.app_a.paid)

    def test_legacy_receipt_list_excludes_foreign_and_unassigned_records(self):
        from django_school_management.payments.models import SSLPayment
        from django_school_management.payments.views import DashboardSSLPaymentsList
        own = SSLPayment.objects.create(transaction_id=1, received_amount=100, institute=self.school_a)
        SSLPayment.objects.create(transaction_id=2, received_amount=100, institute=self.school_b)
        SSLPayment.objects.create(transaction_id=3, received_amount=100)
        view = DashboardSSLPaymentsList()
        view.request = self.request()
        self.assertEqual(list(view.get_queryset()), [own])
