from django.http import Http404, HttpResponseForbidden
from django.http.request import split_domain_port

from .models import Tenant, TenantDomain
from .scoping import request_institute
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.utils.cache import add_never_cache_headers

from django_school_management.accounts.security import MFA_ROUTES, admin_mfa_response


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host, _ = split_domain_port(request.get_host())
        request.tenant = None
        request.is_platform_host = host in getattr(settings, 'PLATFORM_HOSTS', [])
        if request.is_platform_host:
            request.institute = None
            return self._get_response(request)

        if host in ('localhost', '127.0.0.1'):
            request.tenant = Tenant.objects.filter(subdomain='default').first()
            return self._finalize_request(request)

        domain = TenantDomain.objects.filter(domain=host, is_active=True).select_related('tenant').first()
        if domain:
            request.tenant = domain.tenant
            return self._finalize_request(request)

        subdomain = host.split('.')[0]
        tenant = Tenant.objects.filter(subdomain=subdomain).first()
        if tenant:
            request.tenant = tenant
            return self._finalize_request(request)

        raise Http404('Unknown tenant domain.')

    def _get_response(self, request):
        response = self.get_response(request)
        if request.resolver_match and request.resolver_match.url_name in MFA_ROUTES:
            add_never_cache_headers(response)
        return response

    def _finalize_request(self, request):
        if getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False):
            user = request.user
            tenant = getattr(request, 'tenant', None)
            if tenant and not user.is_superuser and user.tenant_id and user.tenant_id != tenant.pk:
                return HttpResponseForbidden('You do not have access to this tenant.')
            if tenant and not user.is_superuser and user.tenant_id is None:
                return HttpResponseForbidden('You must be assigned to a tenant before accessing this school.')
        try:
            request.institute = request_institute(request, required=False)
        except PermissionDenied:
            return HttpResponseForbidden('Your school assignment does not match this domain.')
        return self._get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        route = request.resolver_match
        platform_hosts = getattr(settings, 'PLATFORM_HOSTS', [])
        legacy_admin = route is not None and 'admin' in route.app_names
        platform_admin = route is not None and 'platform' in route.app_names and route.url_name != 'release_notes'
        if (legacy_admin or platform_admin) and platform_hosts:
            host, _ = split_domain_port(request.get_host())
            if host not in platform_hosts:
                return HttpResponseForbidden('Use the platform domain for administrator access.')

        tenant = getattr(request, 'tenant', None)
        if tenant and tenant.status in ('suspended', 'archived') and not getattr(request.user, 'is_superuser', False):
            module = getattr(view_func, '__module__', '')
            name = getattr(view_func, '__name__', '')
            payment_callback = (module, name) in {
                ('django_school_management.billing.views', 'stripe_webhook'),
                ('django_school_management.payments.views', 'paystack_webhook'),
            }
            if not (request.path.startswith('/platform/') or module.startswith('allauth.account.') or payment_callback):
                return HttpResponseForbidden('This school workspace is currently suspended. Contact the school administrator.')
        # The legacy Django admin is not tenant-scoped. Reserve it for platform operators.
        if request.path.startswith('/upload/') and not (request.user.is_authenticated and request.user.is_staff and getattr(request, 'institute', None)):
            return HttpResponseForbidden('School staff access is required for uploads.')
        if legacy_admin and not (request.user.is_active and request.user.is_superuser):
            return HttpResponseForbidden('Platform administrator access is required.')
        if route is not None:
            return admin_mfa_response(request, route.url_name)

