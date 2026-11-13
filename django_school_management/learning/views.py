from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.utils import timezone
from django.db.models import Prefetch
from django.db import transaction
from .models import Assignment, Submission
from .forms import AssignmentForm, SubmissionForm, GradeForm
from .access import school_student, school_teacher


@login_required
def student_assignments(request):
    student = school_student(request)
    submissions = Submission.objects.filter(student=student, tenant=request.tenant)
    assignments = Assignment.objects.filter(tenant=request.tenant,
        academic_class_id=student.academic_class_id).select_related('teacher', 'academic_class').prefetch_related(
            Prefetch('submissions', queryset=submissions, to_attr='own_submissions')) if student.academic_class_id else []
    for assignment in assignments:
        assignment.submission = next(iter(assignment.own_submissions), None)
        assignment.is_overdue = assignment.due_date <= timezone.now()
    return render(request, 'learning/student_assignments.html', {
        'student': student, 'assignments': assignments, 'tenant': request.tenant,
    })


@login_required
@require_POST
def submit_assignment(request, assignment_id):
    student = school_student(request)
    if not student.academic_class_id:
        raise PermissionDenied('Ask the school to assign your class before submitting work.')
    assignment = get_object_or_404(Assignment, pk=assignment_id, tenant=request.tenant,
        academic_class_id=student.academic_class_id)
    form = SubmissionForm(request.POST, request.FILES)
    if assignment.due_date <= timezone.now():
        form.is_valid()
        form.add_error(None, 'The submission deadline has passed.')
    elif form.is_valid():
        with transaction.atomic():
            submission, created = Submission.objects.get_or_create(assignment=assignment, student=student,
                defaults={'tenant': request.tenant, **form.cleaned_data})
        if created:
            messages.success(request, 'Your work has been submitted.')
        else:
            messages.info(request, 'You have already submitted this assignment.')
        return redirect('learning:student_assignments')
    return render(request, 'learning/submit_assignment.html', {'form': form, 'assignment': assignment}, status=400)


@login_required
def teacher_assignments(request):
    teacher = school_teacher(request)
    submissions = Submission.objects.filter(tenant=request.tenant,
        student__admission_student__department_choice__institute=teacher.institute).select_related('student__admission_student')
    assignments = Assignment.objects.filter(tenant=request.tenant, teacher=teacher).select_related('academic_class').prefetch_related(
        Prefetch('submissions', queryset=submissions, to_attr='school_submissions'))
    for assignment in assignments:
        for submission in assignment.school_submissions:
            submission.grade_form = GradeForm(instance=submission, auto_id=f'submission-{submission.pk}-%s')
    return render(request, 'learning/teacher_assignments.html', {
        'teacher': teacher, 'assignments': assignments, 'tenant': request.tenant,
    })


@login_required
def create_assignment(request):
    teacher = school_teacher(request)
    form = AssignmentForm(request.POST or None, request.FILES or None,
        teacher=teacher, tenant=request.tenant)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Assignment published to the selected class.')
        return redirect('learning:teacher_assignments')
    return render(request, 'learning/create_assignment.html', {'form': form},
        status=400 if request.method == 'POST' else 200)


@login_required
@require_POST
def grade_submission(request, submission_id):
    teacher = school_teacher(request)
    with transaction.atomic():
        submission = get_object_or_404(Submission.objects.select_for_update(), pk=submission_id,
            tenant=request.tenant, assignment__tenant=request.tenant, assignment__teacher=teacher,
            student__admission_student__department_choice__institute=teacher.institute)
        form = GradeForm(request.POST, instance=submission)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.graded_at = timezone.now()
            submission.save(update_fields=['grade', 'feedback', 'graded_at'])
            messages.success(request, 'Grade saved.')
            return redirect('learning:teacher_assignments')
    return render(request, 'learning/grade_submission.html', {'form': form, 'submission': submission}, status=400)


@login_required
def portal_home(request):
    if request.user.is_superuser:
        return redirect('platform:overview')
    from django_school_management.tenants.scoping import request_institute
    from django_school_management.parents.models import Guardian
    from django_school_management.accounts.constants import AccountURLConstants
    if request_institute(request, required=False) is not None:
        if school_teacher(request, required=False):
            return redirect('learning:teacher_assignments')
        if school_student(request, required=False):
            return redirect('learning:student_assignments')
        if Guardian.objects.filter(user=request.user, tenant=request.tenant).exists():
            return redirect('parents:parent_dashboard')
    return redirect(AccountURLConstants.profile_complete)
