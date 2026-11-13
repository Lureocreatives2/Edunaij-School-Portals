from django.apps import AppConfig

class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_school_management.audit'
    verbose_name = 'Security & Audit Logs'
