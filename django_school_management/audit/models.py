from django.db import models
from django.conf import settings

class SecurityAuditLog(models.Model):
    """Tracks critical security events across the platform."""
    ACTION_CHOICES = [
        ('login_success', 'Successful Login'),
        ('login_failed', 'Failed Login'),
        ('tenant_suspended', 'Tenant Suspended'),
        ('tenant_reactivated', 'Tenant Reactivated'),
        ('user_role_changed', 'User Role Changed'),
        ('sensitive_data_access', 'Sensitive Data Accessed'),
        ('billing_action', 'Billing Action Performed'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='security_audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='security_audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True, help_text="Additional context (e.g., which student was viewed)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} by {self.user} at {self.created_at}"
