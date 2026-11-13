from django.contrib import admin
from .models import (AcademicSession,
                     Semester, Department,
                     Batch, TempSerialID,
                     Subject)


class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ('year', 'created_by')


class BatchAdmin(admin.ModelAdmin):
    list_display = ('year', 'number', 'department',)


class TempSerialIDAdmin(admin.ModelAdmin):
    list_display = ('year', 'serial', 'department', 'student')


admin.site.register(AcademicSession, AcademicSessionAdmin)
admin.site.register(Batch, BatchAdmin)
admin.site.register(TempSerialID, TempSerialIDAdmin)
admin.site.register(Semester)
admin.site.register(Department)
admin.site.register(Subject)


# ==========================================
# NIGERIAN SCHOOL CUSTOMIZATION ADMIN
# ==========================================
from .models import AcademicTerm, SchoolSection, AcademicClass, ClassArm

@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_current')
    list_editable = ('is_current',)

@admin.register(SchoolSection)
class SchoolSectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)

@admin.register(AcademicClass)
class AcademicClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'section', 'next_class', 'is_active')
    list_filter = ('section', 'is_active')

@admin.register(ClassArm)
class ClassArmAdmin(admin.ModelAdmin):
    list_display = ('academic_class', 'name', 'is_active')
    list_filter = ('academic_class', 'is_active')
