from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django_school_management.accounts.models import User
from django_school_management.academics.models import Department, AcademicClass, AcademicSession, Batch, Semester
from django_school_management.institute.models import InstituteProfile
from django_school_management.students.models import Student, AdmissionStudent
from django_school_management.teachers.models import Teacher, Designation
from django_school_management.parents.models import Guardian, GuardianStudent
from django_school_management.payments.models import PaystackPayment
from django_school_management.tenants.models import Tenant
from .models import Assignment, Submission


@override_settings(ALLOWED_HOSTS=['alpha.testserver', 'beta.testserver', 'testserver'])
class PortalWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alpha = Tenant.objects.create(name='Alpha', slug='alpha', subdomain='alpha', status='active')
        cls.beta = Tenant.objects.create(name='Beta', slug='beta', subdomain='beta', status='active')
        cls.school_a = InstituteProfile.objects.create(name='Alpha', tenant=cls.alpha)
        cls.school_b = InstituteProfile.objects.create(name='Beta', tenant=cls.beta)
        cls.class_one = AcademicClass.objects.create(name='Year 1')
        cls.class_two = AcademicClass.objects.create(name='Year 2')
        cls.school_a.offered_classes.add(cls.class_one, cls.class_two)
        cls.school_b.offered_classes.add(cls.class_one)
        session = AcademicSession.objects.create(year=2026)
        semester = Semester.objects.create(number=1)
        cls.student_user = User.objects.create_user(username='student-a', tenant=cls.alpha, institute=cls.school_a)
        cls.other_user = User.objects.create_user(username='student-b', tenant=cls.beta, institute=cls.school_b)
        cls.teacher_user = User.objects.create_user(username='teacher-a', tenant=cls.alpha, institute=cls.school_a)
        cls.second_teacher_user = User.objects.create_user(username='second-teacher', tenant=cls.alpha, institute=cls.school_a)
        cls.parent_user = User.objects.create_user(username='parent-a', tenant=cls.alpha, institute=cls.school_a)
        for suffix, school, user in [('a', cls.school_a, cls.student_user), ('b', cls.school_b, cls.other_user)]:
            department = Department.objects.create(name='Department '+suffix, short_name=suffix, code=1, institute=school)
            batch = Batch.objects.create(year=session, number=1, department=department)
            applicant = AdmissionStudent.objects.create(name='Child '+suffix, email=suffix+'@example.test', department_choice=department, choosen_department=department)
            student = Student.objects.bulk_create([Student(user=user, academic_class=cls.class_one,
                admission_student=applicant, batch=batch, semester=semester, ac_session=session,
                temporary_id=suffix+'-student', temp_serial='1')])[0]
            setattr(cls, 'student_'+suffix, student)
        designation = Designation.objects.create(title='Teacher')
        cls.teacher = Teacher.objects.create(name='Alpha teacher', employee_id='T1', designation=designation, institute=cls.school_a, user=cls.teacher_user)
        cls.second_teacher = Teacher.objects.create(name='Second teacher', employee_id='T2', designation=designation, institute=cls.school_a, user=cls.second_teacher_user)
        cls.guardian = Guardian.objects.create(user=cls.parent_user, tenant=cls.alpha)
        GuardianStudent.objects.create(guardian=cls.guardian, student=cls.student_a)
        cls.assignment = Assignment.objects.create(title='Alpha homework', tenant=cls.alpha, teacher=cls.teacher,
            academic_class=cls.class_one, description='Explain your answer', due_date=timezone.now()+timedelta(days=2))
        cls.foreign_assignment = Assignment.objects.create(title='Beta secret homework', tenant=cls.beta,
            academic_class=cls.class_one, description='Beta only', due_date=timezone.now()+timedelta(days=2))
        cls.other_class_assignment = Assignment.objects.create(title='Other class homework', tenant=cls.alpha,
            teacher=cls.teacher, academic_class=cls.class_two, description='Year 2 only', due_date=timezone.now()+timedelta(days=2))

    def login(self, user):
        self.client.force_login(user)

    def get(self, path):
        return self.client.get(path, HTTP_HOST='alpha.testserver')

    def post(self, path, data):
        return self.client.post(path, data, HTTP_HOST='alpha.testserver')

    def submit(self):
        self.login(self.student_user)
        response = self.post(f'/learning/assignments/{self.assignment.pk}/submit/', {'text_response': 'My answer'})
        self.assertEqual(response.status_code, 302)
        return Submission.objects.get(assignment=self.assignment, student=self.student_a)

    def test_student_page_renders_only_current_school_and_class(self):
        self.login(self.student_user)
        response = self.get('/learning/assignments/')
        self.assertContains(response, 'Alpha homework')
        self.assertNotContains(response, 'Beta secret homework')
        self.assertNotContains(response, 'Other class homework')

    def test_submit_grade_and_parent_review_complete_journey(self):
        submission = self.submit()
        self.login(self.teacher_user)
        self.assertContains(self.get('/learning/teacher/assignments/'), 'My answer')
        response = self.post(f'/learning/teacher/submission/{submission.pk}/grade/', {'grade': 'A', 'feedback': 'Clear explanation'})
        self.assertEqual(response.status_code, 302)
        self.login(self.student_user)
        self.assertContains(self.get('/learning/assignments/'), 'Clear explanation')
        self.login(self.parent_user)
        self.assertContains(self.get(f'/parents/students/{self.student_a.pk}/'), 'Clear explanation')

    def test_wrong_school_and_class_submission_are_hidden(self):
        self.login(self.student_user)
        for assignment in (self.foreign_assignment, self.other_class_assignment):
            response = self.post(f'/learning/assignments/{assignment.pk}/submit/', {'text_response': 'x'})
            self.assertEqual(response.status_code, 404)
        self.assertEqual(Submission.objects.count(), 0)

    def test_duplicate_submission_does_not_overwrite_work(self):
        submission = self.submit()
        self.post(f'/learning/assignments/{self.assignment.pk}/submit/', {'text_response': 'replacement'})
        submission.refresh_from_db()
        self.assertEqual(submission.text_response, 'My answer')
        self.assertEqual(Submission.objects.count(), 1)

    def test_empty_and_late_submissions_are_rejected(self):
        self.login(self.student_user)
        path = f'/learning/assignments/{self.assignment.pk}/submit/'
        self.assertEqual(self.post(path, {}).status_code, 400)
        Assignment.objects.filter(pk=self.assignment.pk).update(due_date=timezone.now()-timedelta(hours=1))
        self.assertContains(self.post(path, {'text_response': 'Late'}), 'deadline has passed', status_code=400)
        self.assertFalse(Submission.objects.exists())

    def test_student_without_link_cannot_impersonate_by_editable_id(self):
        unlinked = User.objects.create_user(username='unlinked', tenant=self.alpha, institute=self.school_a,
            employee_or_student_id=self.student_a.temporary_id)
        self.login(unlinked)
        self.assertEqual(self.get('/learning/assignments/').status_code, 403)

    def test_only_assignment_teacher_can_grade(self):
        submission = self.submit()
        self.login(self.second_teacher_user)
        response = self.post(f'/learning/teacher/submission/{submission.pk}/grade/', {'grade': 'A'})
        self.assertEqual(response.status_code, 404)
        submission.refresh_from_db()
        self.assertEqual(submission.grade, 'P')

    def test_invalid_grade_is_rejected(self):
        submission = self.submit()
        self.login(self.teacher_user)
        response = self.post(f'/learning/teacher/submission/{submission.pk}/grade/', {'grade': 'INVALID'})
        self.assertEqual(response.status_code, 400)
        submission.refresh_from_db()
        self.assertEqual(submission.grade, 'P')

    def test_mutations_require_post(self):
        self.login(self.student_user)
        self.assertEqual(self.get(f'/learning/assignments/{self.assignment.pk}/submit/').status_code, 405)
        self.login(self.teacher_user)
        self.assertEqual(self.get('/learning/teacher/submission/1/grade/').status_code, 405)

    def test_teacher_can_publish_assignment_and_form_renders(self):
        self.login(self.teacher_user)
        self.assertEqual(self.get('/learning/teacher/assignments/create/').status_code, 200)
        response = self.post('/learning/teacher/assignments/create/', {'title': 'New homework', 'description': 'Work',
            'academic_class': self.class_one.pk, 'due_date': (timezone.now()+timedelta(days=3)).isoformat()})
        self.assertEqual(response.status_code, 302)
        assignment = Assignment.objects.get(title='New homework')
        self.assertEqual(assignment.teacher_id, self.teacher.pk)
        self.assertEqual(assignment.tenant_id, self.alpha.pk)

    def test_parent_cannot_create_or_grade_assignments(self):
        self.login(self.parent_user)
        self.assertEqual(self.get('/learning/teacher/assignments/create/').status_code, 403)
        self.assertEqual(self.post('/learning/teacher/submission/1/grade/', {'grade': 'A'}).status_code, 403)

    def test_parent_dashboard_renders_real_child_data(self):
        self.login(self.parent_user)
        response = self.get('/parents/dashboard/')
        self.assertContains(response, 'Child a')
        self.assertContains(response, 'Year 1')
        self.assertNotContains(response, 'Child b')

    def test_bad_legacy_guardian_link_does_not_expose_foreign_child(self):
        GuardianStudent.objects.bulk_create([GuardianStudent(guardian=self.guardian, student=self.student_b)])
        self.login(self.parent_user)
        self.assertNotContains(self.get('/parents/dashboard/'), 'Child b')
        self.assertEqual(self.get(f'/parents/students/{self.student_b.pk}/').status_code, 404)

    def test_models_reject_cross_school_links(self):
        with self.assertRaises(ValidationError):
            GuardianStudent.objects.create(guardian=self.guardian, student=self.student_b)
        with self.assertRaises(ValidationError):
            Guardian.objects.create(user=self.other_user, tenant=self.alpha)
        self.teacher.user = self.other_user
        with self.assertRaises(ValidationError):
            self.teacher.clean()
        self.student_a.user = self.other_user
        with self.assertRaises(ValidationError):
            self.student_a.clean()

    def test_parent_receipts_exclude_pending_payments(self):
        PaystackPayment.objects.create(institute=self.school_a, student=self.student_a.admission_student,
            transaction_reference='VERIFIED-RECEIPT', amount=100, status='success')
        PaystackPayment.objects.create(institute=self.school_a, student=self.student_a.admission_student,
            transaction_reference='PENDING-RECEIPT', amount=100, status='pending')
        self.login(self.parent_user)
        response = self.get(f'/parents/students/{self.student_a.pk}/')
        self.assertContains(response, 'VERIFIED-RECEIPT')
        self.assertNotContains(response, 'PENDING-RECEIPT')

    def test_assignment_download_checks_class_membership(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            self.assignment.attachment.save('homework.pdf', SimpleUploadedFile('homework.pdf', b'homework'))
            self.login(self.student_user)
            response = self.get(self.assignment.attachment.url)
            self.assertEqual(response.status_code, 200)
            response.close()
            Student.objects.filter(pk=self.student_a.pk).update(academic_class=self.class_two)
            self.assertEqual(self.get(self.assignment.attachment.url).status_code, 404)

    def test_submission_download_only_owner_parent_and_assigned_teacher(self):
        submission = self.submit()
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            submission.file.save('answer.pdf', SimpleUploadedFile('answer.pdf', b'answer'))
            for user in (self.student_user, self.parent_user, self.teacher_user):
                self.login(user)
                response = self.get(submission.file.url)
                self.assertEqual(response.status_code, 200)
                response.close()
            self.login(self.second_teacher_user)
            self.assertEqual(self.get(submission.file.url).status_code, 404)

    def test_invalid_upload_is_rejected(self):
        self.login(self.student_user)
        file = SimpleUploadedFile('attack.html', b'<script>alert(1)</script>')
        response = self.post(f'/learning/assignments/{self.assignment.pk}/submit/', {'file': file})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Submission.objects.exists())

    def test_portal_entry_routes_accounts_by_explicit_links(self):
        for user, target in ((self.student_user, '/learning/assignments/'),
                (self.teacher_user, '/learning/teacher/assignments/'),
                (self.parent_user, '/parents/dashboard/')):
            self.login(user)
            self.assertEqual(self.get('/portal/')['Location'], target)

    def test_foreign_domain_cannot_use_linked_account(self):
        self.login(self.student_user)
        self.assertEqual(self.client.get('/learning/assignments/', HTTP_HOST='beta.testserver').status_code, 403)

    def test_unrelated_same_school_child_is_hidden_from_parent(self):
        other = Student.objects.bulk_create([Student(admission_student=self.student_a.admission_student,
            semester=self.student_a.semester, academic_class=self.class_one)])[0]
        self.login(self.parent_user)
        self.assertEqual(self.get(f'/parents/students/{other.pk}/').status_code, 404)

    def test_student_can_download_only_their_own_photo(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            self.student_a.admission_student.photo.save('child.jpg', SimpleUploadedFile('child.jpg', b'photo'))
            self.login(self.student_user)
            response = self.get(self.student_a.admission_student.photo.url)
            self.assertEqual(response.status_code, 200)
            response.close()
            self.login(self.second_teacher_user)
            self.assertEqual(self.get(self.student_a.admission_student.photo.url).status_code, 404)

    def test_assignment_rejects_teacher_from_another_school(self):
        with self.assertRaises(ValidationError):
            Assignment.objects.create(tenant=self.beta, teacher=self.teacher, academic_class=self.class_one,
                title='Invalid', description='x', due_date=timezone.now()+timedelta(days=1))

    def test_submission_requires_csrf_token_in_browser(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student_user)
        response = client.post(f'/learning/assignments/{self.assignment.pk}/submit/',
            {'text_response': 'No token'}, HTTP_HOST='alpha.testserver')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Submission.objects.exists())

    def test_assignment_form_restricts_school_class_offering(self):
        foreign_class = AcademicClass.objects.create(name='Foreign class only')
        self.school_b.offered_classes.add(foreign_class)
        self.login(self.teacher_user)
        response = self.get('/learning/teacher/assignments/create/')
        self.assertNotContains(response, 'Foreign class only')
        response = self.post('/learning/teacher/assignments/create/', {'title': 'Forbidden class', 'description': 'x',
            'academic_class': foreign_class.pk, 'due_date': (timezone.now()+timedelta(days=3)).isoformat()})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Assignment.objects.filter(title='Forbidden class').exists())
