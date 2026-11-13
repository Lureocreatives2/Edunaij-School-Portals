from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django_school_management.tenants.models import Tenant
from django_school_management.billing.models import Subscription, Invoice, UsageRecord
from django_school_management.billing.services import UsageService, SuspensionService


class BillingServicesTests(TestCase):
    def setUp(self):
        # Create a test tenant
        self.tenant = Tenant.objects.create(
            name='Test Academy',
            slug='test-academy',
            subdomain='test',
            status='active'
        )
        
        # Create a test subscription
        self.subscription = Subscription.objects.create(
            tenant=self.tenant,
            status='active',
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
            auto_renew=True
        )

    def test_usage_service_get_counts(self):
        """Test that UsageService returns a dictionary with expected keys."""
        counts = UsageService.get_usage_counts(self.tenant)
        self.assertIn('students', counts)
        self.assertIn('teachers', counts)
        self.assertIn('classes', counts)
        # Since DB is empty, counts should be 0
        self.assertEqual(counts['students'], 0)

    def test_usage_service_check_quota_allowed(self):
        """Test that quota check allows addition when under limit."""
        is_allowed, current, limit, message = UsageService.check_quota(self.tenant, 'students', requested_addition=10)
        self.assertTrue(is_allowed)
        self.assertEqual(message, "Within quota limits.")

    def test_usage_service_check_quota_exceeded(self):
        """Test that quota check blocks addition when over limit."""
        # Mock the get_usage_counts to return a high number
        with patch.object(UsageService, 'get_usage_counts', return_value={'students': 95, 'teachers': 0, 'classes': 0}):
            is_allowed, current, limit, message = UsageService.check_quota(self.tenant, 'students', requested_addition=10)
            self.assertFalse(is_allowed)
            self.assertIn("Quota exceeded", message)

    def test_suspension_service_grace_period(self):
        """Test that tenants are not suspended if within the 7-day grace period."""
        self.subscription.status = 'past_due'
        # Set period end to 3 days ago (within 7-day grace period)
        self.subscription.current_period_end = timezone.now() - timedelta(days=3)
        self.subscription.save()
        
        suspended_count = SuspensionService.check_and_suspend_past_due_tenants()
        self.assertEqual(suspended_count, 0)
        
        # Refresh from DB
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, 'active')

    def test_suspension_service_exceeds_grace_period(self):
        """Test that tenants ARE suspended if past_due exceeds the 7-day grace period."""
        self.subscription.status = 'past_due'
        # Set period end to 10 days ago (exceeds 7-day grace period)
        self.subscription.current_period_end = timezone.now() - timedelta(days=10)
        self.subscription.save()
        
        suspended_count = SuspensionService.check_and_suspend_past_due_tenants()
        self.assertEqual(suspended_count, 1)
        
        # Refresh from DB
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, 'suspended')

    def test_suspension_service_reactivation(self):
        """Test that a suspended tenant is reactivated on payment."""
        self.tenant.status = 'suspended'
        self.tenant.save()
        
        SuspensionService.reactivate_tenant_on_payment(self.tenant)
        
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, 'active')
        self.assertEqual(self.subscription.status, 'active')
