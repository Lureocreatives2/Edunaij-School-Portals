"""Shared school boundary. Never infer ownership from names or active flags."""
from django.core.exceptions import PermissionDenied
from django_school_management.institute.models import InstituteProfile


def request_institute(request, required=True):
    tenant = getattr(request, 'tenant', None)
    if tenant is None:
        if required:
            raise PermissionDenied('A school domain is required.')
        return None
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        if not user.is_superuser and user.tenant_id != tenant.pk:
            raise PermissionDenied('You do not belong to this school.')
    institute = InstituteProfile.objects.filter(tenant=tenant).first()
    if user and user.is_authenticated and not user.is_superuser and user.institute_id:
        if not institute or user.institute_id != institute.pk:
            raise PermissionDenied('Your school assignment needs administrator attention.')
    if institute is None and required:
        raise PermissionDenied('This school has no assigned institute.')
    return institute


def require_school_staff(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        raise PermissionDenied('School administrator access is required.')
    if getattr(request, 'tenant', None) is None:
        raise PermissionDenied('A school domain is required.')
    return request_institute(request, required=False)
