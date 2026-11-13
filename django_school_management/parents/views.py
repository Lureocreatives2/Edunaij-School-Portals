from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django_school_management.tenants.scoping import request_institute
from django_school_management.learning.models import Assignment, Submission
from django_school_management.payments.models import PaystackPayment
from .models import Guardian


def guardian_wards(request):
    school = request_institute(request)
    guardian = get_object_or_404(Guardian, user=request.user, tenant=request.tenant,
        user__tenant=request.tenant)
    wards = guardian.wards.filter(student__admission_student__department_choice__institute=school).select_related(
        'student__admission_student', 'student__batch', 'student__academic_class')
    return guardian, wards


@login_required
def parent_dashboard(request):
    guardian, wards = guardian_wards(request)
    return render(request, 'parents/dashboard.html', {
        'guardian': guardian, 'wards': wards, 'tenant': request.tenant,
    })


@login_required
def child_progress(request, student_id):
    guardian, wards = guardian_wards(request)
    link = get_object_or_404(wards, student_id=student_id)
    student = link.student
    assignments = Assignment.objects.filter(tenant=request.tenant,
        academic_class_id=student.academic_class_id) if student.academic_class_id else Assignment.objects.none()
    submissions = Submission.objects.filter(student=student, tenant=request.tenant,
        assignment__tenant=request.tenant).select_related('assignment')
    return render(request, 'parents/child_progress.html', {
        'student': student, 'guardian': guardian,
        'results': student.results.select_related('subject', 'semester'),
        'term_results': student.student_results.select_related('subject', 'academic_term', 'academic_session'),
        'assignments': assignments, 'submissions': submissions,
        'payments': PaystackPayment.objects.filter(student=student.admission_student,
            institute=student.admission_student.department_choice.institute, status='success'),
    })
