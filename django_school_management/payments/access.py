from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django_school_management.tenants.scoping import request_institute
from django_school_management.students.models import AdmissionStudent


def payment_applicant(request, pk):
    school = request_institute(request)
    user = getattr(request, 'user', None)
    staff = user and user.is_authenticated and user.is_staff
    if not staff and str(pk) not in request.session.get('admission_applicants', []):
        raise PermissionDenied('Use the browser session that submitted this application.')
    return get_object_or_404(AdmissionStudent, pk=pk, department_choice__institute=school)
