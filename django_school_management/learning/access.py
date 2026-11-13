from django.core.exceptions import PermissionDenied
from django_school_management.tenants.scoping import request_institute
from django_school_management.students.models import Student
from django_school_management.teachers.models import Teacher


def school_student(request, required=True):
    school = request_institute(request)
    student = Student.objects.filter(user=request.user,
        admission_student__department_choice__institute=school,
        user__tenant=request.tenant, user__institute=school).select_related('academic_class', 'admission_student').first()
    if student is None and required:
        raise PermissionDenied('Your student account needs to be linked by the school.')
    return student


def school_teacher(request, required=True):
    school = request_institute(request)
    teacher = Teacher.objects.filter(user=request.user, institute=school,
        user__tenant=request.tenant, user__institute=school).first()
    if teacher is None and required:
        raise PermissionDenied('Your teacher account needs to be linked by the school.')
    return teacher
