from .models import SecurityAuditLog
import logging

logger = logging.getLogger(__name__)

class AuditService:
    @classmethod
    def log_action(cls, action, request=None, user=None, tenant=None, details=None):
        """Centralized method to log security events."""
        try:
            ip = None
            ua = ''
            if request:
                ip = request.META.get('REMOTE_ADDR')
                ua = request.META.get('HTTP_USER_AGENT', '')
                if not user and hasattr(request, 'user') and request.user.is_authenticated:
                    user = request.user
                if not tenant and hasattr(request, 'tenant'):
                    tenant = request.tenant
                    
            SecurityAuditLog.objects.create(
                tenant=tenant,
                user=user,
                action=action,
                ip_address=ip,
                user_agent=ua,
                details=details or {}
            )
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
