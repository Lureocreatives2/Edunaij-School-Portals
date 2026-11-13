from allauth.account.authentication import get_authentication_records
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


ENROLLMENT_ROUTES = {
    'account_reauthenticate', 'account_email', 'account_confirm_email',
    'account_email_verification_sent', 'mfa_index', 'mfa_activate_totp',
}
MFA_ROUTES = {
    'mfa_index', 'mfa_activate_totp', 'mfa_deactivate_totp',
    'mfa_authenticate', 'mfa_reauthenticate', 'mfa_view_recovery_codes',
    'mfa_generate_recovery_codes', 'mfa_download_recovery_codes',
}


def requires_admin_mfa(user):
    return settings.ADMIN_MFA_REQUIRED and user.is_authenticated and (
        user.is_superuser or user.is_staff
        or (user.requested_role == 'admin' and user.approval_status == 'a')
    )


def admin_mfa_response(request, route_name):
    if route_name == 'account_logout' or not requires_admin_mfa(request.user):
        return None
    if route_name == 'mfa_deactivate_totp':
        return HttpResponseForbidden('Administrators must keep an authenticator enrolled.')

    authenticators = Authenticator.objects.filter(user=request.user)
    if not authenticators.filter(type=Authenticator.Type.TOTP).exists():
        if route_name in ENROLLMENT_ROUTES:
            return None
        destination = 'mfa_activate_totp'
    else:
        verified_ids = {
            record.get('id') for record in get_authentication_records(request)
            if record.get('method') == 'mfa'
        }
        if route_name == 'mfa_reauthenticate' or authenticators.filter(pk__in=verified_ids).exists():
            return None
        destination = 'mfa_reauthenticate'

    if request.method not in ('GET', 'HEAD'):
        return HttpResponseForbidden('Complete administrator multi-factor authentication first.')
    response = redirect_to_login(request.get_full_path(), reverse(destination))
    add_never_cache_headers(response)
    return response


class AdminSafeTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if requires_admin_mfa(user):
            raise AuthenticationFailed('Administrator access requires an MFA-verified session.')
        return user, token


class AdminSafeJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if requires_admin_mfa(user):
            raise AuthenticationFailed('Administrator access requires an MFA-verified session.')
        return user
