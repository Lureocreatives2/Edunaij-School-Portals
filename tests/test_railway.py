"""Deployment bootstrap must never escalate an existing school account."""
import os
from io import StringIO
from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.core.mail import EmailMultiAlternatives
from django.test import TestCase, SimpleTestCase, override_settings

from django_school_management.communications.email_backend import ResendBackend


class PlatformBootstrapTests(TestCase):
    def setUp(self):
        self.variables = {
            'BOOTSTRAP_PLATFORM_OWNER': 'True',
            'DJANGO_SUPERUSER_USERNAME': 'platform-owner',
            'DJANGO_SUPERUSER_EMAIL': 'owner@example.test',
            'DJANGO_SUPERUSER_PASSWORD': 'Unique-initial-secret-48!rain',
        }

    def run_bootstrap(self):
        output = StringIO()
        with patch.dict(os.environ, self.variables):
            call_command('bootstrap_platform_owner', stdout=output)
        self.assertNotIn(self.variables['DJANGO_SUPERUSER_PASSWORD'], output.getvalue())

    def test_opt_in_is_required(self):
        self.variables['BOOTSTRAP_PLATFORM_OWNER'] = 'False'
        self.run_bootstrap()
        self.assertFalse(get_user_model().objects.exists())

    def test_owner_created_once_without_password_reset(self):
        self.run_bootstrap()
        owner = get_user_model().objects.get(username='platform-owner')
        self.assertTrue(owner.is_superuser and owner.is_staff and owner.is_active)
        self.assertIsNone(owner.tenant_id)
        self.assertTrue(owner.check_password(self.variables['DJANGO_SUPERUSER_PASSWORD']))
        original = owner.password
        self.variables['DJANGO_SUPERUSER_PASSWORD'] = 'Changed-secret-57!cloud'
        self.run_bootstrap()
        owner.refresh_from_db()
        self.assertEqual(owner.password, original)

    def test_existing_school_account_is_never_promoted(self):
        user = get_user_model().objects.create_user(username='platform-owner', email='school@example.test')
        with self.assertRaises(CommandError):
            self.run_bootstrap()
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)

    def test_email_collision_is_rejected(self):
        get_user_model().objects.create_user(username='school-admin', email='OWNER@example.test')
        with self.assertRaises(CommandError):
            self.run_bootstrap()
        self.assertFalse(get_user_model().objects.filter(is_superuser=True).exists())

    def test_weak_password_is_rejected(self):
        self.variables['DJANGO_SUPERUSER_PASSWORD'] = '123'
        with self.assertRaises(CommandError):
            self.run_bootstrap()
        self.assertFalse(get_user_model().objects.exists())


@override_settings(RESEND_API_KEY='test-only-provider-key')
class ResendBackendTests(SimpleTestCase):
    @patch('django_school_management.communications.email_backend.requests.post')
    def test_html_reply_to_and_attachment_are_preserved(self, post):
        post.return_value = Mock(status_code=200)
        message = EmailMultiAlternatives('School approval', 'Approved', 'sender@example.test',
            ['school@example.test'], bcc=['audit@example.test'], reply_to=['owner@example.test'])
        message.attach_alternative('<p>Approved</p>', 'text/html')
        message.attach('notice.txt', 'Approval notice', 'text/plain')
        self.assertEqual(ResendBackend().send_messages([message]), 1)
        args = post.call_args.kwargs
        self.assertEqual(args['json']['html'], '<p>Approved</p>')
        self.assertEqual(args['json']['bcc'], ['audit@example.test'])
        self.assertEqual(args['json']['reply_to'], ['owner@example.test'])
        self.assertEqual(args['json']['attachments'][0]['content'], 'QXBwcm92YWwgbm90aWNl')
        self.assertFalse(args['allow_redirects'])

    @patch('django_school_management.communications.email_backend.requests.post')
    def test_provider_failure_is_sanitized_and_silent_mode_returns_zero(self, post):
        post.side_effect = RuntimeError('private provider data')
        message = EmailMultiAlternatives('Test', 'Body', 'sender@example.test', ['school@example.test'])
        with self.assertRaisesRegex(RuntimeError, '^Email delivery failed;') as error:
            ResendBackend().send_messages([message])
        self.assertNotIn('private', str(error.exception))
        self.assertEqual(ResendBackend(fail_silently=True).send_messages([message]), 0)
