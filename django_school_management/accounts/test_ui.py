from django.test import TestCase, override_settings
from django.urls import reverse
from django_school_management.tenants import test_isolation as isolation
from django_school_management.academics.models import AcademicClass, Semester
from django_school_management.students.models import Student
from django_school_management.parents.models import Guardian
from .models import User


@override_settings(ALLOWED_HOSTS=['alpha.testserver'])
class WorkspaceUITests(TestCase):
    setUpTestData = isolation.TwoSchoolIsolationTests.__dict__['setUpTestData']

    def setUp(self):
        self.user.requested_role = 'admin'
        self.user.save(update_fields=['requested_role'])
        self.client.force_login(self.user)

    def get(self, name):
        return self.client.get(reverse(name), HTTP_HOST='alpha.testserver')

    def test_overview_uses_actual_school_counts_and_rows(self):
        class_a = AcademicClass.objects.create(name='Alpha class')
        class_b = AcademicClass.objects.create(name='Beta class')
        self.school_a.offered_classes.add(class_a)
        self.school_b.offered_classes.add(class_a, class_b)
        parent = User.objects.create_user(username='parent-a', tenant=self.alpha, institute=self.school_a)
        Guardian.objects.create(user=parent, tenant=self.alpha)
        other = User.objects.create_user(username='parent-b', tenant=self.beta, institute=self.school_b)
        Guardian.objects.create(user=other, tenant=self.beta)
        semester = Semester.objects.create(number=1)
        Student.objects.bulk_create([
            Student(admission_student=self.app_a, semester=semester, academic_class=class_a),
            Student(admission_student=self.app_b, semester=semester, academic_class=class_b),
        ])
        response = self.get('index_view')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response.context['total_students'], 1)
        self.assertEqual(response.context['total_parents'], 1)
        self.assertEqual(response.context['total_classes'], 1)
        self.assertContains(response, 'Alpha child')
        self.assertNotContains(response, 'Beta child')

    def test_workspace_pages_render_with_current_routes(self):
        for name in ('index_view','students:all_student','teachers:all_teacher','billing_dashboard','institute:onboarding_step1','admin:index'):
            response = self.get(name)
            self.assertEqual(response.status_code, 403 if name == 'admin:index' else 200, name)

    def test_sign_in_and_school_home_render_without_a_logo(self):
        self.client.logout()
        self.assertEqual(self.get('account_login').status_code, 200)
        self.assertEqual(self.get('pages:landing').status_code, 200)

    def test_anonymous_dashboard_stays_protected(self):
        self.client.logout()
        self.assertEqual(self.get('index_view').status_code, 302)

    def test_school_dashboard_requires_approved_assigned_administrator(self):
        for updates in ({'requested_role': 'teacher'}, {'is_staff': False},
                        {'approval_status': 'p'}, {'institute': None}):
            with self.subTest(updates=updates):
                User.objects.filter(pk=self.user.pk).update(requested_role='admin', is_staff=True,
                    approval_status='a', institute=self.school_a)
                User.objects.filter(pk=self.user.pk).update(**updates)
                self.assertEqual(self.get('index_view').status_code, 403)
