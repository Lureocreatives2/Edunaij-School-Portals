from django.db.models import Count, Sum, Avg
from django_school_management.students.models import Student
from django_school_management.payments.models import PaystackPayment # Using our new Paystack model
from django_school_management.learning.models import Submission

class ReportService:
    @classmethod
    def get_school_analytics(cls, tenant):
        """Aggregate high-level stats for the school dashboard."""
        total_students = Student.objects.filter(admission_student__department_choice__institute__tenant=tenant).count()
        
        # Fee collection stats (using Paystack payments as an example)
        total_fees_collected = PaystackPayment.objects.filter(
            institute__tenant=tenant, 
            status='success'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        pending_payments_count = PaystackPayment.objects.filter(
            institute__tenant=tenant,
            status__in=['pending', 'failed']
        ).count()

        return {
            'total_students': total_students,
            'total_fees_collected': total_fees_collected,
            'pending_payments_count': pending_payments_count,
        }

    @classmethod
    def get_student_report_data(cls, tenant, student):
        """Fetch report card data strictly scoped to the tenant."""
        # Ensure the student actually belongs to this tenant
        if student.admission_student.department_choice.institute.tenant_id != tenant.pk:
            raise ValueError("Security Violation: Student does not belong to this tenant.")
            
        # Get all graded submissions for this student in this tenant
        graded_submissions = Submission.objects.filter(
            tenant=tenant,
            assignment__tenant=tenant,
            student=student,
            grade__in=['A', 'B', 'C', 'D', 'F'] # Exclude 'P' (Pending)
        ).select_related('assignment', 'assignment__academic_class')
        
        return {
            'student': student,
            'tenant': tenant,
            'submissions': graded_submissions,
        }
