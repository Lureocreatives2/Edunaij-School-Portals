from django.core.validators import MinValueValidator
from model_utils.models import TimeStampedModel
from django_prometheus.models import ExportModelOperationsMixin

from django.db import models
from django.conf import settings
from django.urls import reverse

from django_school_management.students.models import Student
from django_school_management.academics.models import Subject, Semester, Department


class Exam(ExportModelOperationsMixin('exam'), TimeStampedModel):
    EXAM_CHOICES = (
        ('m', 'Mid Term'),
        ('f', 'Final')
    )
    exam_name = models.CharField(
        max_length=1,
        choices=EXAM_CHOICES
    )
    exam_date = models.DateTimeField()

    def __str__(self):
        return f'{self.get_exam_name_display()} - \
            {self.exam_date.year}'


class Result(ExportModelOperationsMixin('result'), TimeStampedModel):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='results'
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE,
        blank=True, null=True
    )
    practical_marks = models.SmallIntegerField(
        blank=True,
        null=True
    )
    theory_marks = models.SmallIntegerField(
        blank=True,
        null=True
    )
    total_marks = models.SmallIntegerField(
        blank=True,
        null=True
    )

    class Meta:
        unique_together =  ('student', 'semester', 'subject')

    def __str__(self):
        return f'{self.student} | {self.subject} | {self.total_marks}'
    
    def save(self, *args, **kwargs):
        if self.theory_marks and self.practical_marks:
            self.total_marks = self.practical_marks + self.theory_marks
        elif self.practical_marks and not self.theory_marks:
            self.total_marks = self.practical_marks
        else:
            self.total_marks = self.theory_marks
        super().save(*args, **kwargs)


class SubjectGroup(ExportModelOperationsMixin('subject_group'), TimeStampedModel):
    """ Keep track of group of subjects that belongs to a
    department, semester
    """
    department = models.ForeignKey(
        Department,
        related_name='subjects',
        on_delete=models.DO_NOTHING
    )
    semester = models.ForeignKey(
        Semester,
        related_name='subjects',
        on_delete=models.CASCADE
    )
    subjects = models.ManyToManyField(Subject, blank=True)

    def __str__(self):
        return f'{self.department} - {self.semester}'
    
    def get_subjects(self):
        return " | ".join([str(sg) for sg in self.subjects.all()])

    def create_resource(self):
        return reverse('result:create_subject_group')



# ==========================================
# NIGERIAN GRADING & ASSESSMENT MODELS
# ==========================================
from django_school_management.academics.models import AcademicClass, AcademicSession, AcademicTerm, Subject

class StudentResult(models.Model):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='student_results')
    academic_class = models.ForeignKey(AcademicClass, on_delete=models.CASCADE)
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    academic_term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    first_ca = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    second_ca = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    assignment_project = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])

    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, editable=False)
    grade = models.CharField(max_length=2, blank=True, editable=False)
    remark = models.CharField(max_length=50, blank=True, editable=False)

    class Meta:
        unique_together = ('student', 'academic_session', 'academic_term', 'subject')
        ordering = ['subject__name']
        verbose_name_plural = "Student Results"

    def save(self, *args, **kwargs):
        self.total_score = self.first_ca + self.second_ca + self.assignment_project + self.exam_score
        
        if self.total_score >= 70: self.grade, self.remark = 'A', 'Excellent'
        elif self.total_score >= 60: self.grade, self.remark = 'B', 'Very Good'
        elif self.total_score >= 50: self.grade, self.remark = 'C', 'Credit'
        elif self.total_score >= 45: self.grade, self.remark = 'D', 'Pass'
        elif self.total_score >= 40: self.grade, self.remark = 'E', 'Fair'
        else: self.grade, self.remark = 'F', 'Fail'
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.subject} ({self.academic_term} {self.academic_session})"
