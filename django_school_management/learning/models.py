from django.db import models
from django.conf import settings
from django.utils import timezone

class Assignment(models.Model):
    """Represents a homework or project assigned by a teacher to a specific class."""
    tenant = models.ForeignKey(
        'tenants.Tenant', 
        on_delete=models.CASCADE, 
        related_name='assignments',
        help_text='The school this assignment belongs to.'
    )
    teacher = models.ForeignKey(
        'teachers.Teacher', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_assignments'
    )
    academic_class = models.ForeignKey(
        'academics.AcademicClass', 
        on_delete=models.CASCADE, 
        related_name='assignments',
        help_text='The class this assignment is for.'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateTimeField()
    attachment = models.FileField(upload_to='assignments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.teacher_id and self.tenant_id:
            if not self.teacher.institute_id or self.teacher.institute.tenant_id != self.tenant_id:
                raise ValidationError({'teacher': 'The teacher must belong to this school.'})
        if self.tenant_id and self.academic_class_id:
            from django_school_management.institute.models import InstituteProfile
            if not InstituteProfile.objects.filter(tenant_id=self.tenant_id,
                    offered_classes__pk=self.academic_class_id).exists():
                raise ValidationError({'academic_class': 'This class is not offered by the school.'})


    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.academic_class})"

    class Meta:
        ordering = ['-due_date']


class Submission(models.Model):
    """Represents a student's submission for a specific assignment."""
    GRADE_CHOICES = [
        ('A', 'A (Excellent)'),
        ('B', 'B (Good)'),
        ('C', 'C (Average)'),
        ('D', 'D (Poor)'),
        ('F', 'F (Fail)'),
        ('P', 'Pending'),
    ]
    
    assignment = models.ForeignKey(
        Assignment, 
        on_delete=models.CASCADE, 
        related_name='submissions'
    )
    student = models.ForeignKey(
        'students.Student', 
        on_delete=models.CASCADE, 
        related_name='submissions'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant', 
        on_delete=models.CASCADE, 
        related_name='submissions',
        help_text='Denormalized for fast tenant-scoped queries.'
    )
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    text_response = models.TextField(blank=True, null=True, help_text="Optional text-based answer")
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES, default='P')
    feedback = models.TextField(blank=True, null=True, help_text="Teacher's feedback on the submission")
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.assignment_id and self.tenant_id and self.assignment.tenant_id != self.tenant_id:
            raise ValidationError({'assignment': 'The assignment must belong to this school.'})
        if self.student_id and self.tenant_id:
            school = self.student.admission_student.department_choice.institute
            if not school or school.tenant_id != self.tenant_id:
                raise ValidationError({'student': 'The student must belong to this school.'})
            if not self.pk and self.assignment_id and self.student.academic_class_id != self.assignment.academic_class_id:
                raise ValidationError({'student': 'The student must be enrolled in the assigned class.'})

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Submission by {self.student} for {self.assignment.title}"

    class Meta:
        unique_together = ('assignment', 'student')
        ordering = ['-submitted_at']
