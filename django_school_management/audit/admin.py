from django.contrib import admin
from .models import SecurityAuditLog

@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'tenant', 'ip_address', 'created_at')
    list_filter = ('action', 'tenant', 'created_at')
    search_fields = ('user__username', 'ip_address', 'details')
    readonly_fields = ('tenant', 'user', 'action', 'ip_address', 'user_agent', 'details', 'created_at')
    
    def has_add_permission(self, request):
        return False  # Audit logs should only be created by the system
        
    def has_change_permission(self, request, obj=None):
        return False  # Audit logs must be immutable
