from django_school_management.tenants.scoping import request_institute, require_school_staff
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.template.loader import get_template
from django_school_management.students.models import Student
from .services import ReportService

# Note: You will need to run: pip install xhtml2pdf
try:
    from xhtml2pdf import pisa
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

@login_required
def school_analytics_dashboard(request):
    require_school_staff(request)
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        return HttpResponseForbidden("Tenant context missing.")

    analytics = ReportService.get_school_analytics(tenant)
    
    context = {
        'tenant': tenant,
        'analytics': analytics,
    }
    return render(request, 'reports/analytics_dashboard.html', context)

@login_required
def generate_report_card_pdf(request, student_id):
    if not PDF_AVAILABLE:
        return HttpResponse("PDF generation library not installed. Run: pip install xhtml2pdf", status=500)

    require_school_staff(request)
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        return HttpResponseForbidden("Tenant context missing.")

    # STRICT TENANT SCOPING: Only fetch students belonging to this tenant
    student = get_object_or_404(Student, id=student_id, admission_student__department_choice__institute=request_institute(request))
    
    try:
        report_data = ReportService.get_student_report_data(tenant, student)
    except ValueError as e:
        return HttpResponseForbidden(str(e))

    # Render HTML template
    template = get_template('reports/report_card_pdf.html')
    html = template.render(report_data)

    # Generate PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Report_Card_{student.id}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Could not generate this report.', status=500)
        
    return response
