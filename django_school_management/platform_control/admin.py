from django.contrib import admin
from .models import ApplicationRelease, PlatformAction
admin.site.register(ApplicationRelease)

@admin.register(PlatformAction)
class PlatformActionAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'actor', 'action', 'target']
    readonly_fields = ['created_at', 'actor', 'action', 'target', 'details']
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
