"""
Tenant-aware access control mixins and decorators.

Enforces that users can only access resources within their assigned tenant.
Platform admins and superusers can access any tenant.
"""

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin


def tenant_required(view_func):
    """
    Decorator to ensure a request has a valid tenant context.
    
    Raises PermissionDenied if:
    - No tenant is resolved for the request
    - User is not authenticated
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant') or not request.tenant:
            raise PermissionDenied("No tenant context available for this request.")
        return view_func(request, *args, **kwargs)
    return wrapper


def tenant_access_required(view_func):
    """
    Decorator to enforce that users can only access their assigned tenant.
    
    Raises PermissionDenied if:
    - User is not authenticated
    - User's tenant does not match request tenant (unless superuser)
    - Request has no tenant
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant') or not request.tenant:
            raise PermissionDenied("No tenant context available for this request.")
        
        if not request.user.can_access_tenant(request.tenant):
            raise PermissionDenied(
                f"You do not have access to tenant {request.tenant.name}."
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper


class TenantRequiredMixin(UserPassesTestMixin):
    """
    Mixin for class-based views requiring a valid tenant context.
    
    Ensures:
    - Request has a resolved tenant
    - User is authenticated
    - User can access the tenant
    """
    
    def test_func(self):
        """Test that user can access their assigned tenant."""
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            return False
        
        if not self.request.user.is_authenticated:
            return False
        
        return self.request.user.can_access_tenant(self.request.tenant)
    
    def handle_no_permission(self):
        """Return a clear error when access is denied."""
        raise PermissionDenied(
            "You do not have permission to access this resource. "
            "Please verify your tenant assignment."
        )


class PlatformAdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin for views that require platform admin or superuser status.
    
    Used for platform-level admin functions that should not be accessible
    to school admins or regular users.
    """
    
    def test_func(self):
        """Test that user is a superuser or platform admin."""
        if not self.request.user.is_authenticated:
            return False
        
        # TODO: Add platform admin role check when roles are implemented
        # For now, only superusers can access platform admin views
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        """Return a clear error when access is denied."""
        raise PermissionDenied(
            "You do not have permission to access this platform admin function."
        )
