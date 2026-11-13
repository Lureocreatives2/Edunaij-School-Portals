from types import SimpleNamespace
from django.test import TestCase, RequestFactory, override_settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from rest_framework.test import APIRequestFactory, force_authenticate
from django_school_management.accounts.models import User
from django_school_management.academics.models import Department
from django_school_management.institute.models import InstituteProfile
from django_school_management.institute.views import _resolve_institute, InstituteProfileConfigDashboard, onboarding_step2
from django_school_management.students.models import AdmissionStudent
from django_school_management.students.api.views import AdmissionStudentViewSet, StudentViewSet
from django_school_management.teachers.models import Teacher
from django_school_management.teachers.views import teacher_detail_view
from .models import Tenant
from .scoping import request_institute


class TwoSchoolIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alpha = Tenant.objects.create(name='Alpha', slug='alpha', subdomain='alpha', status='active')
        cls.beta = Tenant.objects.create(name='Beta', slug='beta', subdomain='beta', status='active')
        cls.school_a = InstituteProfile.objects.create(name='Alpha', tenant=cls.alpha, active=True)
        cls.school_b = InstituteProfile.objects.create(name='Beta', tenant=cls.beta, active=True)
        cls.user = User.objects.create_user(username='alpha', email='alpha@example.com', tenant=cls.alpha, institute=cls.school_a, is_staff=True, approval_status='a')
        cls.dept_a = Department.objects.create(name='Alpha group', short_name='A', code=1, institute=cls.school_a)
        cls.dept_b = Department.objects.create(name='Beta group', short_name='B', code=2, institute=cls.school_b)
        cls.app_a = AdmissionStudent.objects.create(name='Alpha child', department_choice=cls.dept_a)
        cls.app_b = AdmissionStudent.objects.create(name='Beta child', department_choice=cls.dept_b)

    def request(self, method='get', data=None, tenant=None):
        req = getattr(APIRequestFactory(), method)('/', data or {}, format='json')
        req.tenant = tenant or self.alpha
        force_authenticate(req, user=self.user)
        return req

    def test_admissions_list_excludes_other_school(self):
        response = AdmissionStudentViewSet.as_view({'get': 'list'})(self.request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r['id'] for r in response.data['results']], [self.app_a.pk])

    def test_foreign_admission_detail_is_hidden(self):
        response = AdmissionStudentViewSet.as_view({'get': 'retrieve'})(self.request(), pk=self.app_b.pk)
        self.assertEqual(response.status_code, 404)

    def test_foreign_admission_write_is_hidden(self):
        response = AdmissionStudentViewSet.as_view({'patch': 'partial_update'})(self.request('patch', {'paid': True}), pk=self.app_b.pk)
        self.assertEqual(response.status_code, 404)
        self.app_b.refresh_from_db()
        self.assertFalse(self.app_b.paid)

    def test_foreign_department_reference_is_rejected(self):
        response = AdmissionStudentViewSet.as_view({'patch': 'partial_update'})(self.request('patch', {'department_choice': self.dept_b.pk}), pk=self.app_a.pk)
        self.assertEqual(response.status_code, 400)
        self.app_a.refresh_from_db()
        self.assertEqual(self.app_a.department_choice_id, self.dept_a.pk)

    def test_statistics_are_scoped(self):
        response = AdmissionStudentViewSet.as_view({'get': 'statistics'})(self.request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_applications'], 1)

    def test_token_user_cannot_use_another_school_domain(self):
        response = AdmissionStudentViewSet.as_view({'get': 'list'})(self.request(tenant=self.beta))
        self.assertEqual(response.status_code, 403)

    def test_inconsistent_user_assignment_is_denied(self):
        self.user.institute = self.school_b
        req = RequestFactory().get('/')
        req.user, req.tenant = self.user, self.alpha
        with self.assertRaises(PermissionDenied):
            request_institute(req)

    def test_onboarding_never_adopts_another_active_school(self):
        empty = Tenant.objects.create(name='Empty', slug='empty', subdomain='empty')
        self.user.tenant, self.user.institute = empty, None
        req = RequestFactory().get('/')
        req.user, req.tenant = self.user, empty
        self.assertIsNone(_resolve_institute(req))
        self.assertIsNone(self.user.institute_id)

    def test_school_settings_cannot_edit_another_school(self):
        req = RequestFactory().get('/')
        req.user, req.tenant = self.user, self.alpha
        with self.assertRaises(Http404):
            InstituteProfileConfigDashboard.as_view()(req, institute_pk=self.school_b.pk)

    def test_non_staff_cannot_onboard(self):
        self.user.is_staff = False
        req = RequestFactory().get('/')
        req.user, req.tenant = self.user, self.alpha
        with self.assertRaises(PermissionDenied):
            onboarding_step2(req)

    @override_settings(ALLOWED_HOSTS=['alpha.testserver'], PLATFORM_HOSTS=[])
    def test_legacy_admin_is_reserved_for_platform_admins(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        response = self.client.get(reverse('admin:index'), HTTP_HOST='alpha.testserver')
        self.assertEqual(response.status_code, 403)

    def test_student_bulk_action_cannot_change_another_school(self):
        from django_school_management.academics.models import Semester, AcademicSession, Batch
        from django_school_management.students.models import Student
        semester = Semester.objects.create(number=1)
        year = AcademicSession.objects.create(year=2026)
        batch_a = Batch.objects.create(year=year, number=1, department=self.dept_a)
        batch_b = Batch.objects.create(year=year, number=1, department=self.dept_b)
        students = Student.objects.bulk_create([
            Student(admission_student=self.app_a, semester=semester, batch=batch_a),
            Student(admission_student=self.app_b, semester=semester, batch=batch_b),
        ])
        response = StudentViewSet.as_view({'post': 'bulk_action'})(self.request('post', {'action': 'deactivate', 'student_ids': [s.pk for s in students]}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['affected_count'], 1)
        self.assertTrue(Student._base_manager.get(pk=students[0].pk).is_dropped)
        self.assertFalse(Student._base_manager.get(pk=students[1].pk).is_dropped)

    def test_teacher_from_another_school_is_hidden(self):
        from django_school_management.teachers.models import Designation
        designation = Designation.objects.create(title='Teacher')
        teacher = Teacher.objects.create(name='Beta teacher', employee_id='B1', institute=self.school_b, designation=designation)
        req = RequestFactory().get('/')
        req.user, req.tenant = self.user, self.alpha
        with self.assertRaises(Http404):
            teacher_detail_view.__wrapped__(req, pk=teacher.pk)

    def test_migration_links_only_unambiguous_user_assignments(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        migrate = import_module('django_school_management.institute.migrations.0018_tenant_ownership').link_unambiguous_schools
        InstituteProfile.objects.update(tenant=None)
        migrate(apps, SimpleNamespace(connection=connection))
        self.school_a.refresh_from_db()
        self.school_b.refresh_from_db()
        self.assertEqual(self.school_a.tenant_id, self.alpha.pk)
        self.assertIsNone(self.school_b.tenant_id)

    def test_migration_does_not_guess_conflicting_ownership(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        User.objects.create_user(username='conflict', institute=self.school_a, tenant=self.beta)
        InstituteProfile.objects.update(tenant=None)
        migrate = import_module('django_school_management.institute.migrations.0018_tenant_ownership').link_unambiguous_schools
        migrate(apps, SimpleNamespace(connection=connection))
        self.school_a.refresh_from_db()
        self.assertIsNone(self.school_a.tenant_id)

    def test_public_admission_department_uses_school_domain(self):
        from django_school_management.students.forms import StudentForm
        req = RequestFactory().get('/')
        req.tenant = self.alpha
        school = request_institute(req)
        self.assertEqual(list(StudentForm(institute=school).fields['department_choice'].queryset), [self.dept_a])

    def test_onboarding_does_not_claim_unowned_departments(self):
        from unittest.mock import patch
        orphan = Department.objects.create(name='Unassigned group', short_name='U', code=9)
        req = RequestFactory().get('/')
        req.user, req.tenant = self.user, self.alpha
        with patch('django_school_management.institute.views.render', return_value=HttpResponse()):
            response = onboarding_step2(req)
        self.assertEqual(response.status_code, 200)
        orphan.refresh_from_db()
        self.assertIsNone(orphan.institute_id)

    def test_onboarding_year_does_not_edit_shared_session(self):
        from django_school_management.academics.models import AcademicSession
        year = AcademicSession.objects.create(year=2026)
        self.school_a.current_session = year
        self.school_a.save(update_fields=['current_session'])
        req = RequestFactory().post('/', {'year': '2027', 'departments-TOTAL_FORMS': '0', 'departments-INITIAL_FORMS': '0'})
        req.user, req.tenant = self.user, self.alpha
        response = onboarding_step2(req)
        self.assertEqual(response.status_code, 302)
        year.refresh_from_db()
        self.assertEqual(year.year, 2026)
        self.assertTrue(AcademicSession.objects.filter(year=2027).exists())

    def test_account_edit_requires_administrator(self):
        from django_school_management.accounts.views import UserUpdateView
        req = RequestFactory().get('/')
        req.user, req.tenant = self.user, self.alpha
        view = UserUpdateView()
        view.request = req
        with self.assertRaises(PermissionDenied):
            view.test_func()

    def test_account_edit_cannot_target_other_school_or_superuser(self):
        from django_school_management.accounts.views import UserUpdateView
        other = User.objects.create_user(username='beta', tenant=self.beta, institute=self.school_b)
        platform = User.objects.create_user(username='platform', tenant=self.alpha, institute=self.school_a)
        User.objects.filter(pk=platform.pk).update(is_superuser=True)
        req = RequestFactory().get('/')
        req.user, req.tenant = self.user, self.alpha
        view = UserUpdateView()
        view.request = req
        self.assertFalse(view.get_queryset().filter(pk=other.pk).exists())
        self.assertFalse(view.get_queryset().filter(pk=platform.pk).exists())

    def test_anonymous_account_edit_is_denied(self):
        from django.contrib.auth.models import AnonymousUser
        from django_school_management.accounts.views import UserUpdateView
        req = RequestFactory().get('/')
        req.user, req.tenant = AnonymousUser(), self.alpha
        view = UserUpdateView()
        view.request = req
        with self.assertRaises(PermissionDenied):
            view.test_func()
