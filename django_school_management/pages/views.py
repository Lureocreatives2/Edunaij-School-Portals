from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from django_school_management.academics.models import Department
from django_school_management.students.forms import StudentForm
from django_school_management.students.models import AdmissionStudent
from django_school_management.tenants.scoping import request_institute
from django_school_management.articles.models import Article
from django_school_management.students.tasks import send_admission_confirmation_email


def index(request):
    if getattr(request, 'is_platform_host', False):
        return render(request, 'platform/landing.html')
    blog_count = Article.objects.count()
    departments = Department.objects.filter(institute=request_institute(request))
    if blog_count >= 3:
        recent_blogs = Article.objects.order_by('-created')[:3]
    else:
        recent_blogs = Article.objects.order_by('-created')[:blog_count]
    ctx = {
        'recent_blogs': recent_blogs,
        'departments': departments,
    }
    return render(request, 'website/index.html', ctx)


def online_admission(request):
    institute = request_institute(request)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, institute=institute)
        if form.is_valid():
            data = form.save()
            ids = request.session.get('admission_applicants', [])
            request.session['admission_applicants'] = (ids + [str(data.pk)])[-20:]
            return render(request, 'pages/students/application_submitted.html', {
                'applicant': data, 'institute': institute,
                'checkout_available': bool(settings.PAYSTACK_SECRET_KEY and institute.admission_fee and institute.admission_fee > 0),
            })
    else:
        form = StudentForm(institute=institute)
    # For template JS: show JSC section only when applying for class 9-10 (BD school/madrasah)
    show_jsc_conditional = (
        institute and getattr(institute, 'country', None) and
        str(getattr(institute.country, 'code', institute.country)) == 'BD' and
        getattr(institute, 'is_school_or_madrasah', False)
    )
    # For template JS: show admit_to_semester only when HSC Science (BD polytechnic)
    show_admit_semester_conditional = (
        institute and getattr(institute, 'country', None) and
        str(getattr(institute.country, 'code', institute.country)) == 'BD' and
        getattr(institute, 'is_polytechnic', False)
    )
    return render(request, 'pages/students/admission.html', {
        'form': form,
        'institute': institute,
        'show_jsc_conditional': show_jsc_conditional,
        'show_admit_semester_conditional': show_admit_semester_conditional,
    })


def online_admission_payment(request, pk):
    from django_school_management.payments.access import payment_applicant
    from django.http import HttpResponse
    payment_applicant(request, pk)
    return HttpResponse('This payment method is unavailable. Please contact the school.', status=503)


def payment(request, pk):
    from django_school_management.payments.access import payment_applicant
    from django.http import HttpResponse
    payment_applicant(request, pk)
    return HttpResponse('This payment method is unavailable. Please contact the school.', status=503)
