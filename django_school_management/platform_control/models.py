from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator


class ApplicationRelease(models.Model):
    version = models.CharField(max_length=50, unique=True, validators=[RegexValidator(r'^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$', 'Use a version such as 1.2.0.')])
    notes = models.TextField(max_length=20000)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.version


class PlatformAction(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=40)
    target = models.CharField(max_length=200)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SchoolRegistration(models.Model):
    class SchoolType(models.TextChoices):
        NURSERY = 'nursery', 'Early years or nursery'
        PRIMARY = 'primary', 'Primary'
        SECONDARY = 'secondary', 'Secondary'
        COMBINED = 'combined', 'Primary and secondary'
        POLYTECHNIC = 'polytechnic', 'Polytechnic'

    class Ownership(models.TextChoices):
        PRIVATE = 'private', 'Private or non-state'
        PUBLIC = 'public', 'Public or government'

    class CACStatus(models.TextChoices):
        REGISTERED = 'registered', 'Registered'
        PENDING = 'pending', 'Application pending'
        NOT_STARTED = 'not_started', 'Not yet registered'

    class ApprovalStatus(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        PENDING = 'pending', 'Application pending'
        NOT_STARTED = 'not_started', 'Not yet applied'

    school_name = models.CharField(max_length=160)
    school_type = models.CharField(max_length=16, choices=SchoolType.choices)
    contact_name = models.CharField(max_length=120)
    contact_email = models.EmailField()
    ownership = models.CharField(max_length=10, choices=Ownership.choices, blank=True)
    state = models.CharField('state or FCT', max_length=20, blank=True)
    lga = models.CharField('LGA or area council', max_length=100, blank=True)
    campus_address = models.CharField(max_length=250, blank=True)
    contact_role = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=16, blank=True)
    cac_status = models.CharField('CAC registration status', max_length=14, choices=CACStatus.choices, blank=True)
    cac_legal_name = models.CharField('name on CAC certificate', max_length=200, blank=True)
    cac_number = models.CharField('CAC registration number', max_length=50, blank=True)
    approval_status = models.CharField('education approval status', max_length=14, choices=ApprovalStatus.choices, blank=True)
    approval_authority = models.CharField('issuing education authority', max_length=150, blank=True)
    approval_reference = models.CharField('education approval reference', max_length=80, blank=True)
    school_code = models.CharField('school or EMIS code', max_length=60, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at', '-pk']
        constraints = [models.UniqueConstraint(
            fields=['school_name', 'contact_email'], name='unique_school_registration_contact',
        )]

    def __str__(self):
        return self.school_name
