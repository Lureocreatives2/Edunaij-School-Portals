from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import (
    SECRET_SESSION_KEY, format_hotp_value, hotp_value, yield_hotp_counters_from_time,
)

from django_school_management.institute.models import InstituteProfile
from django_school_management.tenants.models import Tenant


@override_settings(
    ADMIN_MFA_REQUIRED=True,
    PLATFORM_HOSTS=['platform.test'],
    ALLOWED_HOSTS=['platform.test', 'alpha.test'],
    SCHOOL_EMAIL_DOMAIN='schools.edunaij.test',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class AdministratorMFATests(TestCase):
    password = 'Test-administrator-password-679!'

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.owner = user_model.objects.create_superuser(
            username='owner', email='owner@example.test', password=cls.password,
        )
        cls.tenant = Tenant.objects.create(name='Alpha', slug='alpha', subdomain='alpha')
        school = InstituteProfile.objects.create(name='Alpha', tenant=cls.tenant)
        cls.official = user_model.objects.create_user(
            username='admin-alpha', email='admin-alpha@example.test',
            tenant=cls.tenant, institute=school, is_staff=True,
            requested_role='admin', approval_status='a',
        )

    def test_owner_enrollment_and_verified_session(self):
        host = 'platform.test'
        login = reverse('platform:login')
        overview = reverse('platform:overview')
        self.client.post(login, {'login': self.owner.email, 'password': self.password}, HTTP_HOST=host)
        response = self.client.get(overview, HTTP_HOST=host, follow=True)
        self.assertEqual(response.request['PATH_INFO'], reverse('mfa_activate_totp'))
        self.assertContains(response, 'Authenticator code')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.post(reverse('platform:plans'), HTTP_HOST=host).status_code, 403)

        secret = self.client.session[SECRET_SESSION_KEY]
        counter = next(yield_hotp_counters_from_time())
        code = format_hotp_value(hotp_value(secret, counter))
        response = self.client.post(reverse('mfa_activate_totp'), {'code': code}, HTTP_HOST=host)
        self.assertRedirects(response, reverse('mfa_view_recovery_codes'), fetch_redirect_response=False)
        self.assertTrue(Authenticator.objects.filter(user=self.owner, type='totp').exists())
        response = self.client.get(overview, HTTP_HOST=host, follow=True)
        self.assertEqual(response.request['PATH_INFO'], reverse('mfa_reauthenticate'))
        response = self.client.post(
            reverse('mfa_reauthenticate') + '?next=' + overview, {'code': code}, HTTP_HOST=host,
        )
        self.assertRedirects(response, overview, fetch_redirect_response=False)
        self.assertEqual(self.client.get(overview, HTTP_HOST=host).status_code, 200)
        self.assertEqual(self.client.get(reverse('mfa_deactivate_totp'), HTTP_HOST=host).status_code, 403)

        self.client.logout()
        response = self.client.post(login, {'login': self.owner.email, 'password': self.password}, HTTP_HOST=host)
        self.assertRedirects(response, reverse('mfa_authenticate'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(reverse('mfa_authenticate'), HTTP_HOST=host).status_code, 200)

    def test_school_admin_is_gated_and_assigned_address_is_separate(self):
        self.client.force_login(self.official)
        response = self.client.get(reverse('index_view'), HTTP_HOST='alpha.test')
        self.assertTrue(response.url.startswith(reverse('mfa_activate_totp') + '?'))
        self.assertEqual(self.tenant.assigned_email, f'school-{self.tenant.pk}@schools.edunaij.test')
        self.assertEqual(self.official.assigned_school_email,
                         f'official-{self.tenant.pk}-{self.official.pk}@schools.edunaij.test')
        self.assertEqual(self.official.email, 'admin-alpha@example.test')
        self.official.approval_status = 'p'
        self.assertEqual(self.official.assigned_school_email, '')
