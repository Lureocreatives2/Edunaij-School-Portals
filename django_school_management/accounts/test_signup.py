from django.test import TestCase, override_settings
from django.urls import reverse
from django_school_management.tenants.models import Tenant
from django_school_management.institute.models import InstituteProfile
from .models import User


@override_settings(PLATFORM_HOSTS=[], ALLOWED_HOSTS=['localhost'], EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SignupTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Nice College', slug='nice-college', subdomain='default')
        self.school = InstituteProfile.objects.create(name='Nice College', tenant=self.tenant)

    def test_signup_without_logo_renders(self):
        response = self.client.get(reverse('account_signup'), HTTP_HOST='localhost')
        self.assertContains(response, 'Create my account')

    def test_signup_is_school_linked_and_not_privileged(self):
        response = self.client.post(reverse('account_signup'), {
            'email': 'new-person@example.test', 'username': 'new-person',
            'password1': 'A-unique-test-password-8742!', 'password2': 'A-unique-test-password-8742!',
            'is_staff': True, 'is_superuser': True, 'requested_role': 'admin',
        }, HTTP_HOST='localhost', follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='new-person')
        self.assertEqual(user.tenant_id, self.tenant.pk)
        self.assertEqual(user.institute_id, self.school.pk)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotEqual(user.approval_status, 'a')
        self.assertEqual(user.requested_role, 'subscriber')
        self.client.logout()
        response = self.client.post(reverse('account_login'), {'login': user.email,
            'password': 'A-unique-test-password-8742!'}, HTTP_HOST='localhost', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session.get('_auth_user_id'), str(user.pk))


    def test_signup_displays_validation_errors(self):
        response = self.client.post(reverse('account_signup'), {'email':'invalid','username':'bad',
            'password1':'short','password2':'different'}, HTTP_HOST='localhost')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(User.objects.exists())
