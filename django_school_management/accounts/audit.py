"""
Audit logging for sensitive operations.

Records login attempts, role changes, tenant changes, and other security-relevant events.
"""

import logging
from django.contrib.auth import user_logged_in, user_login_failed
from django.dispatch import receiver
from django.utils import timezone

from .models import AuditLog

logger = logging.getLogger('audit')


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_audit_event(
    operation,
    actor,
    tenant=None,
    description=None,
    details=None,
    content_type=None,
    object_id=None,
    request=None
):
    """
    Log an audit event.
    
    Args:
        operation: Operation type (from OPERATION_CHOICES)
        actor: User who performed the action
        tenant: Tenant context (if applicable)
        description: Human-readable description
        details: Additional metadata dict
        content_type: ContentType of affected object
        object_id: ID of affected object
        request: HTTP request (for IP and user agent)
    """
    audit_entry = AuditLog(
        operation=operation,
        actor=actor,
        tenant=tenant,
        description=description or '',
        details=details or {},
        content_type=content_type,
        object_id=object_id,
    )
    
    if request:
        audit_entry.ip_address = get_client_ip(request)
        audit_entry.user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    audit_entry.save()
    logger.info(f"Audit: {operation} by {actor} at {audit_entry.created_at}")


# Signal handlers for automatic audit logging

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful login."""
    log_audit_event(
        operation='login',
        actor=user,
        tenant=getattr(request, 'tenant', None),
        description=f"User {user.username} logged in",
        request=request
    )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """Log failed login attempt."""
    username = credentials.get('username', 'unknown')
    log_audit_event(
        operation='login_failed',
        actor=None,
        description=f"Failed login attempt for {username}",
        details={'attempted_username': username},
        request=request
    )
