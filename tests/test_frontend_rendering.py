from django.test import TestCase, override_settings
from django.urls import reverse
from django_school_management.tenants import test_isolation as isolation


@override_settings(ALLOWED_HOSTS=['alpha.testserver'], ADMIN_MFA_REQUIRED=False)
class FrontendRenderingTests(TestCase):
    setUpTestData = isolation.TwoSchoolIsolationTests.__dict__['setUpTestData']

    def setUp(self):
        self.user.requested_role = 'admin'
        self.user.save(update_fields=['requested_role'])
        self.client.force_login(self.user)

    def test_school_forms_and_lists_render_after_framework_upgrade(self):
        for name in ('academics:departments', 'academics:academic_sessions',
                     'academics:create_academic_session', 'students:all_applicants'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name), HTTP_HOST='alpha.testserver')
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'vendor/bootstrap/bootstrap.bundle.min.js')

    def test_monthly_report_pdf_survives_frontend_upgrade(self):
        response = self.client.get(reverse('students:counsel_monthly_report_typed',
            kwargs={'response_type': 'pdf'}), HTTP_HOST='alpha.testserver')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
