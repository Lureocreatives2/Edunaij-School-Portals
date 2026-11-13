from django.contrib import admin
from .models import Assignment, Submission

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'academic_class', 'teacher', 'tenant', 'due_date')
    list_filter = ('tenant', 'academic_class', 'due_date')
    search_fields = ('title', 'description')
    raw_id_fields = ('teacher', 'academic_class')

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'grade', 'submitted_at', 'graded_at')
    list_filter = ('grade', 'tenant', 'submitted_at')
    search_fields = ('student__admission_student__name', 'assignment__title')
    raw_id_fields = ('student', 'assignment')
