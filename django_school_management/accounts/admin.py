from rolepermissions.roles import assign_role
from rolepermissions.admin import RolePermissionsUserAdminMixin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin

from .models import CustomGroup, CommonUserProfile, SocialLink
from .forms import UserRegistrationForm, UserChangeForm
from .audit import AuditLog

User = get_user_model()


class UserResource(resources.ModelResource):
    class Meta:
        model = User


class CustomUserAdmin(auth_admin.UserAdmin):

    form = UserChangeForm
    add_form = UserRegistrationForm
    model = User
    fieldsets = (
        ("School assignment", {"fields": ("tenant", "institute")}),
        ("User", {"fields": ("approval_status", "requested_role")}),
    ) + auth_admin.UserAdmin.fieldsets
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "email", "password1", "password2", "is_staff",
                "is_active", "is_superuser", "groups", "user_permissions"
            )}
         ),
    )
    list_display = ["username", "is_superuser", "approval_status", "requested_role"]
    list_editable = ["approval_status", "requested_role", ]
    search_fields = ["approval_status", "requested_role"]
    resource_class = UserResource


class UserProfileResource(resources.ModelResource):
    class Meta:
        model = CommonUserProfile


class UserProfileAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = UserProfileResource


class CustomGroupAdmin(GroupAdmin):
    list_display = ('id', 'name', 'group_creator')


class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('operation', 'actor', 'tenant', 'created_at')
    list_filter = ('operation', 'tenant', 'created_at')
    search_fields = ('actor__username', 'description', 'details')
    readonly_fields = (
        'operation', 'actor', 'tenant', 'description', 'details',
        'ip_address', 'user_agent', 'created_at', 'content_type', 'object_id'
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation of audit logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of audit logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of audit logs."""
        return False


admin.site.register(CommonUserProfile, UserProfileAdmin)
admin.site.register(CustomGroup, CustomGroupAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(AuditLog, AuditLogAdmin)
