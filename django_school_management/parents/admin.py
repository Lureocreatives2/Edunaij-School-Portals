from django.contrib import admin
from .models import Guardian, GuardianStudent

@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'phone_number', 'created_at')
    list_filter = ('tenant',)
    search_fields = ('user__username', 'user__email', 'phone_number')
    raw_id_fields = ('user',)

@admin.register(GuardianStudent)
class GuardianStudentAdmin(admin.ModelAdmin):
    list_display = ('guardian', 'student', 'relationship', 'emergency_contact')
    list_filter = ('relationship', 'emergency_contact', 'guardian__tenant')
    search_fields = ('student__admission_student__name', 'guardian__user__username')
    raw_id_fields = ('guardian', 'student')
