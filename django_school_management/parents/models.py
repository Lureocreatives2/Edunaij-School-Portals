from django.db import models
from django.conf import settings
from django.utils import timezone

class Guardian(models.Model):
    """Links a User to a specific Tenant (School) as a Guardian."""
    tenant = models.ForeignKey(
        'tenants.Tenant', 
        on_delete=models.CASCADE, 
        related_name='guardians',
        help_text='The school this guardian is associated with.'
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='guardian_profile'
    )
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.user_id and self.tenant_id and self.user.tenant_id != self.tenant_id:
            raise ValidationError({'user': 'The guardian account must belong to this school.'})

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Guardian: {self.user.get_full_name() or self.user.username} ({self.tenant.name})"

    class Meta:
        unique_together = ('tenant', 'user') # A user can only be a guardian once per school


class GuardianStudent(models.Model):
    """Links a Guardian to one or more Students within the same Tenant."""
    RELATIONSHIP_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Legal Guardian'),
        ('other', 'Other'),
    ]
    
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name='wards')
    student = models.ForeignKey(
        'students.Student', 
        on_delete=models.CASCADE, 
        related_name='guardians'
    )
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default='guardian')
    emergency_contact = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.guardian_id and self.student_id:
            school = self.student.admission_student.department_choice.institute
            if not school or school.tenant_id != self.guardian.tenant_id:
                raise ValidationError({'student': 'The child must belong to the guardian school.'})

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.guardian.user.username} -> {self.student}"

    class Meta:
        unique_together = ('guardian', 'student')
