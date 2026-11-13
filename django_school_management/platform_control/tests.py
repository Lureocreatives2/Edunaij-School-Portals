from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django_school_management.accounts.models import User
from django_school_management.tenants.models import Tenant, BillingPlan
from django_school_management.institute.models import InstituteProfile
from django_school_management.billing.models import Subscription
from .models import ApplicationRelease, PlatformAction, SchoolRegistration


@override_settings(ALLOWED_HOSTS=['localhost','platform.test'], PLATFORM_HOSTS=['platform.test'])
class PlatformOwnerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_superuser(username='owner', email='owner@example.test', password='Test-owner-password-928!')
        cls.alpha = Tenant.objects.create(name='Alpha school', slug='alpha', subdomain='default', status='active')
        cls.beta = Tenant.objects.create(name='Beta school', slug='beta', subdomain='beta', status='active')
        cls.school = InstituteProfile.objects.create(name='Alpha school', tenant=cls.alpha)
        cls.admin = User.objects.create_user(username='school-admin', email='admin@example.test', tenant=cls.alpha,
            institute=cls.school, is_staff=True, requested_role='admin', approval_status='a')
        cls.plan = BillingPlan.objects.create(name='Basic',slug='basic',price=1000)
        Subscription.objects.create(tenant=cls.alpha, status='active')

    def get(self, name, **kwargs):
        return self.client.get(reverse(name,kwargs=kwargs), HTTP_HOST='localhost' if name in ('index_view', 'platform:release_notes') else 'platform.test')

    def post(self, name, data=None, **kwargs):
        return self.client.post(reverse(name,kwargs=kwargs),data or {},HTTP_HOST='platform.test')

    def test_owner_overview_contains_all_school_organisations(self):
        self.client.force_login(self.owner)
        response=self.get('platform:overview')
        self.assertContains(response,'Alpha school')
        self.assertContains(response,'Beta school')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response.context['school_count'],2)
        self.assertEqual(response.context['subscription_count'],1)

    def test_school_admin_cannot_read_or_mutate_platform(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.get('platform:overview').status_code,403)
        response=self.post('platform:school',{'status':'suspended','billing_plan':self.plan.pk},pk=self.beta.pk)
        self.assertEqual(response.status_code,403)
        self.beta.refresh_from_db()
        self.assertEqual(self.beta.status,'active')

    def test_anonymous_owner_entry_redirects_to_platform_login(self):
        response=self.get('platform:overview')
        self.assertEqual(response.status_code,302)
        self.assertIn('/platform/login/',response['Location'])
        self.assertEqual(self.get('platform:login').status_code,200)

    def test_owner_can_assign_plan_and_suspend_without_faking_subscription_payment(self):
        self.client.force_login(self.owner)
        response=self.post('platform:school',{'status':'suspended','billing_plan':self.plan.pk},pk=self.alpha.pk)
        self.assertEqual(response.status_code,302)
        self.alpha.refresh_from_db()
        self.assertEqual(self.alpha.status,'suspended')
        self.assertEqual(self.alpha.billing_plan_id,self.plan.pk)
        self.assertEqual(Subscription.objects.get(tenant=self.alpha).status,'active')
        self.assertTrue(PlatformAction.objects.filter(action='school_configuration').exists())
        self.client.force_login(self.admin)
        self.assertEqual(self.get('index_view').status_code,403)
        self.client.logout()
        self.assertEqual(self.get('platform:login').status_code,200)
        self.client.force_login(self.owner)
        self.assertEqual(self.get('platform:overview').status_code,200)

    def test_release_publish_is_post_only_idempotent_and_visible_in_school(self):
        release=ApplicationRelease.objects.create(version='1.2.0',notes='New school features',created_by=self.owner)
        self.client.force_login(self.admin)
        self.assertEqual(self.get('platform:release_notes',pk=release.pk).status_code,404)
        self.assertEqual(self.post('platform:publish_release',pk=release.pk).status_code,403)
        self.client.force_login(self.owner)
        self.assertEqual(self.get('platform:publish_release',pk=release.pk).status_code,405)
        self.assertEqual(self.post('platform:publish_release',pk=release.pk).status_code,302)
        self.post('platform:publish_release',pk=release.pk)
        self.assertEqual(PlatformAction.objects.filter(action='release_published').count(),1)
        self.client.force_login(self.admin)
        self.assertContains(self.get('platform:release_notes',pk=release.pk),'New school features')
        self.assertContains(self.get('index_view'),'Platform update 1.2.0')

    def test_platform_hostname_needs_no_school_tenant(self):
        self.client.force_login(self.owner)
        response=self.client.get('/platform/',HTTP_HOST='platform.test')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Beta school')

    def test_signed_payment_callbacks_can_reach_verification_for_suspended_school(self):
        Tenant.objects.filter(pk=self.alpha.pk).update(status='suspended')
        response=self.client.post('/dashboard/payments/paystack/webhook/',data='{}',content_type='application/json',HTTP_HOST='localhost')
        self.assertEqual(response.status_code,401)

    def test_owner_login_routes_to_platform_home(self):
        self.client.force_login(self.owner)
        response=self.get('portal_home')
        self.assertEqual(response['Location'],reverse('platform:overview'))

    def test_owner_can_create_plan_and_release_draft(self):
        self.client.force_login(self.owner)
        response=self.post('platform:plans',{'name':'Growth','slug':'growth','price':'2000',
            'billing_cycle':'monthly','max_students':200,'max_teachers':20,'max_classes':10,'is_active':'on'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(BillingPlan.objects.filter(slug='growth').exists())
        response=self.post('platform:releases',{'version':'1.0.0','notes':'First platform release'})
        self.assertEqual(response.status_code,302)
        self.assertIsNone(ApplicationRelease.objects.get(version='1.0.0').published_at)

    def test_platform_owner_can_sign_in_with_email(self):
        response=self.client.post(reverse('platform:login'),{'login':'owner@example.test',
            'password':'Test-owner-password-928!'},HTTP_HOST='platform.test',follow=True)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.request['PATH_INFO'],reverse('platform:overview'))

    def test_edunaij_branding_and_restrained_sign_in(self):
        response=self.get('platform:login')
        self.assertContains(response,'Sign in to edunaij')
        self.assertContains(response,'edunaij-platform.css')
        self.assertNotContains(response,'nc-auth-art')
        self.client.force_login(self.owner)
        response=self.get('platform:overview')
        self.assertContains(response,'ej-platform')
        self.assertContains(response,'edunaij')

    def test_school_host_blocks_even_platform_owner(self):
        self.client.force_login(self.owner)
        for name in ('platform:overview', 'platform:login', 'admin:index'):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name), HTTP_HOST='localhost').status_code, 403)


    @override_settings(ADMIN_MFA_REQUIRED=False)
    def test_public_school_registration_and_owner_review(self):
        registration = reverse('platform:register_school')
        review = reverse('platform:school_registrations')
        host = 'platform.test'
        details = {
            'school_name': 'Oakfield College', 'school_type': 'secondary',
            'contact_name': 'Fictional School Contact', 'contact_email': 'Contact@Oakfield.test',
            'ownership': 'private', 'state': 'Lagos', 'lga': 'Ikeja',
            'campus_address': '1 Sample Road', 'contact_role': 'Principal',
            'contact_phone': '+234 803 000 0000', 'cac_status': 'registered',
            'cac_legal_name': 'Oakfield College Ltd', 'cac_number': 'RC EXAMPLE-123',
            'approval_status': 'approved', 'approval_authority': 'Sample education office',
            'approval_reference': 'EXAMPLE/SCHOOL/01',
        }
        self.assertContains(self.client.get(registration, HTTP_HOST=host), 'Register your school')
        self.assertEqual(Client(enforce_csrf_checks=True).post(registration, details, HTTP_HOST=host).status_code, 403)
        invalid = {**details, 'contact_email': 'invalid'}
        self.assertEqual(self.client.post(registration, invalid, HTTP_HOST=host).status_code, 400)
        self.assertFalse(SchoolRegistration.objects.exists())
        incomplete = {**details, 'cac_number': '', 'approval_reference': ''}
        response = self.client.post(registration, incomplete, HTTP_HOST=host)
        self.assertEqual(response.status_code, 400)
        self.assertIn('cac_number', response.context['form'].errors)
        self.assertIn('approval_reference', response.context['form'].errors)
        for _ in range(2):
            response = self.client.post(registration, details, HTTP_HOST=host, follow=True)
            self.assertContains(response, 'Registration request received')
            self.assertNotContains(response, 'Contact@Oakfield.test')
        self.assertEqual(SchoolRegistration.objects.filter(contact_email='contact@oakfield.test').count(), 1)
        self.assertEqual(SchoolRegistration.objects.get().contact_phone, '+2348030000000')
        self.assertFalse(Tenant.objects.filter(name='Oakfield College').exists())
        public = {**details, 'school_name': 'Sample Public School', 'ownership': 'public',
                  'cac_status': '', 'cac_legal_name': '', 'cac_number': '', 'approval_status': '',
                  'approval_authority': '', 'approval_reference': ''}
        response = self.client.post(registration, public, HTTP_HOST=host)
        self.assertRedirects(response, reverse('platform:registration_received'))
        self.assertEqual(self.client.get(review, HTTP_HOST=host).status_code, 302)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(review, HTTP_HOST=host).status_code, 403)
        self.client.force_login(self.owner)
        response = self.client.get(review, HTTP_HOST=host)
        self.assertContains(response, 'Oakfield College')
        self.assertContains(response, 'RC EXAMPLE-123')
        self.assertContains(response, 'EXAMPLE/SCHOOL/01')


    def test_public_platform_home_links_to_registration(self):
        response = self.client.get('/', HTTP_HOST='platform.test')
        self.assertTemplateUsed(response, 'platform/landing.html')
        self.assertContains(response, reverse('platform:register_school'))
        self.assertContains(response, 'mailto:opeyemiolamide882@gmail.com')
