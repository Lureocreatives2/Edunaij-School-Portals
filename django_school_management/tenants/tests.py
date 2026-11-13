from django.test import TestCase, override_settings, RequestFactory
from django.http import HttpResponse

from django_school_management.accounts.models import User
from django_school_management.tenants.middleware import TenantMiddleware
from django_school_management.tenants.models import Tenant, TenantDomain


class TenantFoundationTests(TestCase):
    databases = '__all__'

    def test_tenant_model_can_be_created(self):
        tenant = Tenant.objects.create(
            name='Alpha Academy',
            slug='alpha-academy',
            subdomain='alpha',
            status='trial',
        )

        self.assertEqual(tenant.name, 'Alpha Academy')
        self.assertEqual(tenant.subdomain, 'alpha')

    @override_settings(ALLOWED_HOSTS=['beta.example.com', 'testserver', 'localhost', '127.0.0.1'])
    def test_tenant_middleware_sets_request_tenant_from_host(self):
        tenant = Tenant.objects.create(
            name='Beta Academy',
            slug='beta-academy',
            subdomain='beta',
            status='active',
        )
        TenantDomain.objects.create(
            tenant=tenant,
            domain='beta.example.com',
            is_primary=True,
            is_active=True,
        )

        request = RequestFactory().get('/', HTTP_HOST='beta.example.com')
        response = TenantMiddleware(lambda req: HttpResponse('ok'))(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.tenant, tenant)

    @override_settings(ALLOWED_HOSTS=['alpha.example.com', 'beta.example.com', 'testserver', 'localhost', '127.0.0.1'])
    def test_tenant_middleware_blocks_authenticated_user_from_other_tenant(self):
        alpha = Tenant.objects.create(
            name='Alpha Academy',
            slug='alpha-academy',
            subdomain='alpha',
            status='active',
        )
        beta = Tenant.objects.create(
            name='Beta Academy',
            slug='beta-academy',
            subdomain='beta',
            status='active',
        )
        TenantDomain.objects.create(
            tenant=alpha,
            domain='alpha.example.com',
            is_primary=True,
            is_active=True,
        )
        TenantDomain.objects.create(
            tenant=beta,
            domain='beta.example.com',
            is_primary=True,
            is_active=True,
        )

        user = User.objects.create_user(
            username='beta-user',
            email='beta@example.com',
            password='StrongPass123',
            tenant=beta,
        )

        request = RequestFactory().get('/', HTTP_HOST='alpha.example.com')
        request.user = user
        response = TenantMiddleware(lambda req: HttpResponse('ok'))(request)

        self.assertEqual(response.status_code, 403)

    def test_security_defaults_for_platform(self):
        self.assertTrue(__import__('django').conf.settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertTrue(__import__('django').conf.settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(__import__('django').conf.settings.ACCOUNT_LOGIN_METHODS, {'email'})
        self.assertEqual(
            __import__('django').conf.settings.ACCOUNT_SIGNUP_FIELDS,
            ['email*', 'username*', 'password1*', 'password2*'],
        )


class SchoolOnboardingTests(TestCase):
    """
    Phase 03: School Onboarding and Domain Assignment Tests
    
    Tests for:
    - Billing plan creation and management
    - School onboarding workflow
    - Domain registration and validation
    - Onboarding status tracking
    """
    databases = '__all__'
    
    def setUp(self):
        """Create test data for onboarding tests."""
        # Create a platform admin user
        self.platform_admin = User.objects.create_user(
            username='platform-admin',
            email='admin@edunaija.com',
            password='AdminPass123',
        )
        self.platform_admin.is_superuser = True
        self.platform_admin.is_staff = True
        self.platform_admin.save()
        
        # Create sample billing plans
        from django_school_management.tenants.models import BillingPlan
        
        self.starter_plan = BillingPlan.objects.create(
            name='Starter',
            slug='starter',
            description='Perfect for small schools',
            price=9999.00,
            billing_cycle='monthly',
            max_students=100,
            max_teachers=10,
            max_classes=5,
            support_level='community',
            is_active=True,
        )
        
        self.professional_plan = BillingPlan.objects.create(
            name='Professional',
            slug='professional',
            description='For growing schools',
            price=29999.00,
            billing_cycle='monthly',
            max_students=500,
            max_teachers=50,
            max_classes=20,
            support_level='email',
            is_active=True,
            is_recommended=True,
        )
        
        self.free_trial_plan = BillingPlan.objects.create(
            name='Free Trial',
            slug='free-trial',
            description='30-day free trial',
            price=0.00,
            billing_cycle='trial',
            max_students=50,
            max_teachers=5,
            max_classes=3,
            support_level='community',
            is_active=True,
        )
    
    def test_billing_plan_creation(self):
        """Test that billing plans can be created."""
        self.assertEqual(self.starter_plan.name, 'Starter')
        self.assertEqual(self.starter_plan.price, 9999.00)
        self.assertEqual(self.starter_plan.max_students, 100)
        self.assertTrue(self.starter_plan.is_active)
    
    def test_billing_plan_string_representation(self):
        """Test billing plan string format."""
        expected = f"{self.starter_plan.name} - Monthly"
        self.assertEqual(str(self.starter_plan), expected)
    
    def test_school_can_be_onboarded_with_plan(self):
        """Test that a school can be created with a billing plan."""
        from django.utils import timezone
        
        school = Tenant.objects.create(
            name='EduNaija Test School',
            slug='edunaija-test-school',
            subdomain='test-school',
            status='onboarding_in_progress',
            billing_plan=self.professional_plan,
            created_by=self.platform_admin,
        )
        school.start_onboarding()
        
        self.assertEqual(school.billing_plan, self.professional_plan)
        self.assertEqual(school.status, 'onboarding_in_progress')
        self.assertIsNotNone(school.onboarding_started_at)
        self.assertEqual(school.created_by, self.platform_admin)
    
    def test_subdomain_uniqueness_enforced(self):
        """Test that subdomain uniqueness is enforced."""
        Tenant.objects.create(
            name='Alpha School',
            slug='alpha-school',
            subdomain='alpha',
            billing_plan=self.starter_plan,
        )
        
        # Attempt to create duplicate subdomain
        with self.assertRaises(Exception):  # IntegrityError
            Tenant.objects.create(
                name='Another Alpha School',
                slug='another-alpha',
                subdomain='alpha',
                billing_plan=self.starter_plan,
            )
    
    def test_school_slug_generation_from_name(self):
        """Test slug generation from school name."""
        from django.utils.text import slugify
        
        school = Tenant.objects.create(
            name='St. Mary\'s Academy',
            slug=slugify('St. Mary\'s Academy'),
            subdomain='st-marys',
            billing_plan=self.starter_plan,
        )
        
        self.assertEqual(school.slug, 'st-marys-academy')
    
    def test_custom_domain_registration(self):
        """Test registering a custom domain for a school."""
        school = Tenant.objects.create(
            name='EduNaija School',
            slug='edunaija-school',
            subdomain='edunaija-school',
            billing_plan=self.professional_plan,
        )
        
        custom_domain = TenantDomain.objects.create(
            tenant=school,
            domain='school.edu.ng',
            is_primary=False,
            verification_status='pending',
        )
        
        self.assertEqual(custom_domain.tenant, school)
        self.assertEqual(custom_domain.domain, 'school.edu.ng')
        self.assertEqual(custom_domain.verification_status, 'pending')
    
    def test_custom_domain_uniqueness(self):
        """Test that domain uniqueness is enforced."""
        school1 = Tenant.objects.create(
            name='School 1',
            slug='school-1',
            subdomain='school-1',
            billing_plan=self.starter_plan,
        )
        school2 = Tenant.objects.create(
            name='School 2',
            slug='school-2',
            subdomain='school-2',
            billing_plan=self.starter_plan,
        )
        
        TenantDomain.objects.create(
            tenant=school1,
            domain='shared-domain.edu.ng',
        )
        
        # Attempt to register same domain for school2
        with self.assertRaises(Exception):  # IntegrityError
            TenantDomain.objects.create(
                tenant=school2,
                domain='shared-domain.edu.ng',
            )
    
    def test_domain_verification_status_tracking(self):
        """Test domain verification status transitions."""
        school = Tenant.objects.create(
            name='EduNaija School',
            slug='edunaija-school',
            subdomain='edunaija-school',
            billing_plan=self.professional_plan,
        )
        
        domain = TenantDomain.objects.create(
            tenant=school,
            domain='school.edu.ng',
            verification_status='pending',
        )
        
        # Mark as verified
        domain.verification_status = 'verified'
        domain.save()
        
        self.assertTrue(domain.is_verified())
        self.assertEqual(domain.verification_status, 'verified')
    
    def test_onboarding_completion_workflow(self):
        """Test school onboarding completion."""
        from django.utils import timezone
        
        school = Tenant.objects.create(
            name='EduNaija School',
            slug='edunaija-school',
            subdomain='edunaija-school',
            status='onboarding_in_progress',
            billing_plan=self.professional_plan,
            created_by=self.platform_admin,
        )
        school.start_onboarding()
        
        # Complete onboarding
        school.complete_onboarding()
        
        self.assertTrue(school.onboarding_completed)
        self.assertEqual(school.status, 'active')
        self.assertIsNotNone(school.onboarding_completed_at)
    
    def test_school_status_transitions(self):
        """Test valid school status transitions."""
        school = Tenant.objects.create(
            name='EduNaija School',
            slug='edunaija-school',
            subdomain='edunaija-school',
            status='onboarding_pending',
            billing_plan=self.free_trial_plan,
        )
        
        # Pending -> In Progress
        school.status = 'onboarding_in_progress'
        school.save()
        self.assertEqual(school.status, 'onboarding_in_progress')
        
        # In Progress -> Completed
        school.complete_onboarding()
        self.assertEqual(school.status, 'active')
        
        # Active -> Suspended (for non-payment)
        school.status = 'suspended'
        school.save()
        self.assertEqual(school.status, 'suspended')
    
    def test_onboarding_form_validation(self):
        """Test school onboarding form validation."""
        from django_school_management.tenants.forms import SchoolOnboardingForm
        
        # Valid form
        valid_data = {
            'name': 'New School',
            'subdomain': 'new-school',
            'plan': self.starter_plan.id,
            'primary_color': '#0f172a',
            'secondary_color': '#2563eb',
            'custom_domain': '',
        }
        form = SchoolOnboardingForm(data=valid_data)
        self.assertTrue(form.is_valid())
        
        # Invalid subdomain (duplicate)
        Tenant.objects.create(
            name='Existing School',
            slug='existing-school',
            subdomain='existing-school',
            billing_plan=self.starter_plan,
        )
        
        invalid_data = {
            'name': 'Another School',
            'subdomain': 'existing-school',  # Duplicate
            'plan': self.starter_plan.id,
            'primary_color': '#0f172a',
            'secondary_color': '#2563eb',
            'custom_domain': '',
        }
        form = SchoolOnboardingForm(data=invalid_data)
        self.assertFalse(form.is_valid())
    
    def test_onboarding_form_saves_with_plan(self):
        """Test that onboarding form saves school with plan."""
        from django_school_management.tenants.forms import SchoolOnboardingForm
        
        form_data = {
            'name': 'Onboarded School',
            'subdomain': 'onboarded-school',
            'plan': self.professional_plan.id,
            'primary_color': '#0f172a',
            'secondary_color': '#2563eb',
            'custom_domain': '',
        }
        
        form = SchoolOnboardingForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        school = form.save(user=self.platform_admin)
        
        self.assertEqual(school.name, 'Onboarded School')
        self.assertEqual(school.billing_plan, self.professional_plan)
        self.assertEqual(school.created_by, self.platform_admin)
        self.assertEqual(school.status, 'onboarding_in_progress')
    
    def test_school_branding_fields(self):
        """Test school branding fields."""
        school = Tenant.objects.create(
            name='EduNaija School',
            slug='edunaija-school',
            subdomain='edunaija-school',
            primary_color='#FF0000',
            secondary_color='#00FF00',
            billing_plan=self.professional_plan,
        )
        
        self.assertEqual(school.primary_color, '#FF0000')
        self.assertEqual(school.secondary_color, '#00FF00')
    
    def test_school_isolation_by_tenant(self):
        """Test that schools are properly isolated by tenant."""
        school1 = Tenant.objects.create(
            name='School 1',
            slug='school-1',
            subdomain='school-1',
            billing_plan=self.starter_plan,
        )
        school2 = Tenant.objects.create(
            name='School 2',
            slug='school-2',
            subdomain='school-2',
            billing_plan=self.starter_plan,
        )
        
        # Create users bound to different schools
        user1 = User.objects.create_user(
            username='user1',
            email='user1@school1.com',
            password='Pass123',
            tenant=school1,
        )
        user2 = User.objects.create_user(
            username='user2',
            email='user2@school2.com',
            password='Pass123',
            tenant=school2,
        )
        
        # Verify isolation
        self.assertEqual(user1.tenant, school1)
        self.assertEqual(user2.tenant, school2)
        self.assertNotEqual(user1.tenant, user2.tenant)
