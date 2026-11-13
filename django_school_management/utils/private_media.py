"""Serve only database-referenced media after checking its school and viewer."""
import mimetypes
from django.http import FileResponse, Http404
from django.core.exceptions import PermissionDenied
from django_school_management.tenants.scoping import request_institute


def school_media(request, name):
    from django_school_management.institute.models import InstituteProfile
    from django_school_management.tenants.models import Tenant
    from django_school_management.students.models import AdmissionStudent
    from django_school_management.teachers.models import Teacher
    from django_school_management.learning.models import Assignment, Submission
    from django_school_management.parents.models import GuardianStudent
    from django_school_management.articles.models import Article
    from django_school_management.academics.models import Subject, Department
    from django_school_management.notices.models import Notice, NoticeDocument
    from django.utils import timezone
    school = request_institute(request)
    # Public school branding is explicitly allowed; arbitrary files are never served.
    for model, scope, fields in (
        (InstituteProfile, {'pk': school.pk}, ('logo', 'logo_small', 'site_favicon')),
        (Tenant, {'pk': request.tenant.pk}, ('logo',)),
    ):
        for field in fields:
            obj = model.objects.filter(**scope, **{field: name}).first()
            if obj:
                return media_response(getattr(obj, field), public=True)
    for model, scope, fields in (
        (Department, {'institute': school}, ('department_icon',)),
        (Subject, {}, ('book_cover',)),
        (Notice, {'uploaded_by__tenant': request.tenant, 'expires_at__gte': timezone.localdate()}, ('file',)),
        (NoticeDocument, {'notice__uploaded_by__tenant': request.tenant, 'notice__expires_at__gte': timezone.localdate()}, ('file',)),
    ):
        for field in fields:
            obj = model.objects.filter(**scope, **{field: name}).first()
            if obj:
                return media_response(getattr(obj, field), public=True)
    article = Article.published.filter(featured_image=name, author__tenant=request.tenant).first()
    if article:
        return media_response(article.featured_image, public=True)
    user = getattr(request, 'user', None)
    staff = user and user.is_authenticated and user.is_staff
    student = teacher_record = None
    if user and user.is_authenticated:
        from django_school_management.learning.access import school_student, school_teacher
        student = school_student(request, required=False)
        teacher_record = school_teacher(request, required=False)
    for field in ('photo', 'marksheet_image'):
        applicant = AdmissionStudent.objects.filter(department_choice__institute=school, **{field: name}).first()
        if applicant:
            own_session = str(applicant.pk) in request.session.get('admission_applicants', [])
            guardian = user and user.is_authenticated and GuardianStudent.objects.filter(guardian__user=user, guardian__tenant=request.tenant, student__admission_student=applicant).exists()
            if staff or own_session or guardian or (student and student.admission_student_id == applicant.pk):
                return media_response(getattr(applicant, field))
            raise Http404()
    if user and user.is_authenticated:
        teacher = Teacher.objects.filter(institute=school, photo=name).first()
        if teacher:
            return media_response(teacher.photo)
        from django_school_management.accounts.models import CommonUserProfile
        for field in ('profile_picture', 'cover_picture'):
            profiles = CommonUserProfile.objects.filter(user__tenant=request.tenant, **{field: name})
            if not staff:
                profiles = profiles.filter(user=user)
            profile = profiles.first()
            if profile:
                return media_response(getattr(profile, field))
    assignment = Assignment.objects.filter(tenant=request.tenant, attachment=name).first()
    if assignment:
        class_member = student and student.academic_class_id == assignment.academic_class_id
        guardian = user and user.is_authenticated and GuardianStudent.objects.filter(
            guardian__user=user, guardian__tenant=request.tenant,
            student__admission_student__department_choice__institute=school,
            student__academic_class=assignment.academic_class).exists()
        if staff or class_member or guardian or (teacher_record and assignment.teacher_id == teacher_record.pk):
            return media_response(assignment.attachment)
    submission = Submission.objects.filter(tenant=request.tenant, assignment__tenant=request.tenant,
        student__admission_student__department_choice__institute=school, file=name).select_related('assignment').first()
    if submission:
        guardian = user and user.is_authenticated and GuardianStudent.objects.filter(
            guardian__user=user, guardian__tenant=request.tenant, student_id=submission.student_id).exists()
        if staff or guardian or (student and submission.student_id == student.pk) or (
                teacher_record and submission.assignment.teacher_id == teacher_record.pk):
            return media_response(submission.file)
    raise Http404()


def media_response(field, public=False):
    kind = mimetypes.guess_type(field.name)[0]
    inline = kind in ('image/png', 'image/jpeg', 'image/gif', 'image/webp')
    try:
        response = FileResponse(field.open('rb'), as_attachment=not inline,
            content_type=kind if inline else 'application/octet-stream')
    except (OSError, ValueError):
        raise Http404()
    response['Cache-Control'] = 'private, no-store'
    response['Vary'] = 'Cookie, Authorization'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
