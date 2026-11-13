from django.contrib import admin
from .models import Teacher, Designation


admin.site.register(Designation)
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_id', 'institute', 'user')
    search_fields = ('name', 'employee_id', 'user__username')