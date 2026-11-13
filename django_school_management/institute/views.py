from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db import models, transaction
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django_school_management.tenants.scoping import request_institute, require_school_staff
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView

from django_school_management.academics.models import Department, AcademicSession
from django_school_management.institute.forms.institute_profile_form import InstituteProfileCreateForm
from django_school_management.institute.forms.onboarding_forms import (
    OnboardingStep1Form,
    OnboardingDepartmentFormSet,
    OnboardingAcademicSessionForm,
    LoadSubjectsFromCurriculumForm,
)
from .models import InstituteProfile


# ──────────────────────────────────────────────
# Existing config views (kept for settings pages)
# ──────────────────────────────────────────────

class SchoolSettingsMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        require_school_staff(request)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        institute = request_institute(self.request)
        return InstituteProfile.objects.filter(pk=institute.pk)


class InstituteProfileConfigListView(SchoolSettingsMixin, ListView):
    model = InstituteProfile
    context_object_name = 'institute_profiles'
    template_name = 'institute/dashboard/institute_profile_list.html'


class InstituteProfileConfigDashboard(SchoolSettingsMixin, UpdateView):
    model = InstituteProfile
    form_class = InstituteProfileCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    pk_url_kwarg = 'institute_pk'
    template_name = 'institute/dashboard/config_form.html'


class InstituteProfileSetupDashboard(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return redirect('institute:onboarding_step1')


class InstituteProfileDetailDashboard(SchoolSettingsMixin, DetailView):
    model = InstituteProfile
    pk_url_kwarg = 'institute_pk'
    template_name = 'institute/dashboard/config.html'

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        institute_fields = serializers.serialize("python", self.get_queryset())
        ctx['institute_fields'] = institute_fields
        return ctx


class SetActiveInstituteProfile(SchoolSettingsMixin, View):
    def post(self, request, institute_pk, *args, **kwargs):
        from django.shortcuts import get_object_or_404
        institute = get_object_or_404(self.get_queryset(), pk=institute_pk)
        institute.active = True
        institute.save()
        return redirect('institute:institute_detail', institute_pk)


# ──────────────────────────────────────────────
# Onboarding Wizard
# ──────────────────────────────────────────────

ONBOARDING_STEPS = [
    {'number': 1, 'title': 'Institute Profile', 'icon': 'fas fa-school'},
    {'number': 2, 'title': 'Academics', 'icon': 'fas fa-graduation-cap'},
    {'number': 3, 'title': 'Load Subjects', 'icon': 'fas fa-book'},
    {'number': 4, 'title': 'Review & Launch', 'icon': 'fas fa-rocket'},
]


def _onboarding_context(current_step):
    steps = []
    for s in ONBOARDING_STEPS:
        steps.append({
            **s,
            'status': 'completed' if s['number'] < current_step
            else 'active' if s['number'] == current_step
            else 'upcoming',
        })
    return {'onboarding_steps': steps, 'current_step': current_step}


def _resolve_institute(request):
    return require_school_staff(request)


@login_required
def onboarding_step1(request):
    """Step 1: Institute profile — name, country, logo, motto."""
    institute = _resolve_institute(request)

    if request.method == 'POST':
        form = OnboardingStep1Form(
            request.POST, request.FILES,
            instance=institute,
        )
        if form.is_valid():
            inst = form.save(commit=False)
            inst.active = True
            if not inst.created_by_id:
                inst.created_by = request.user
            inst.tenant = request.tenant
            with transaction.atomic():
                # Serialize first-time setup for the same school.
                from django_school_management.tenants.models import Tenant
                Tenant.objects.select_for_update().get(pk=request.tenant.pk)
                if not inst.pk and InstituteProfile.objects.filter(tenant=request.tenant).exists():
                    raise PermissionDenied('This school has already been configured.')
                inst.save()
                request.user.institute = inst
                request.user.save(update_fields=['institute'])
            return redirect('institute:onboarding_step2')
    else:
        form = OnboardingStep1Form(instance=institute)

    ctx = {
        'form': form,
        **_onboarding_context(1),
    }
    return render(request, 'institute/onboarding/step1.html', ctx)


@login_required
def onboarding_step2(request):
    """Step 2: Departments + Academic Session."""
    institute = _resolve_institute(request)
    if not institute:
        return redirect('institute:onboarding_step1')

    existing_departments = Department.objects.filter(institute=institute)
    existing_session = institute.current_session

    if request.method == 'POST':
        dept_formset = OnboardingDepartmentFormSet(
            request.POST, prefix='departments',
        )
        session_form = OnboardingAcademicSessionForm(
            request.POST,
        )
        if dept_formset.is_valid() and session_form.is_valid():
            existing_names = set(
                existing_departments.values_list('name', flat=True)
            )
            for dept_form in dept_formset:
                name = dept_form.cleaned_data.get('name', '').strip()
                if not name or name in existing_names:
                    continue
                Department.objects.create(
                    name=name,
                    short_name=dept_form.cleaned_data.get('short_name', ''),
                    code=dept_form.cleaned_data.get('code') or 0,
                    institute=institute,
                    created_by=request.user,
                )
                existing_names.add(name)
            session, _ = AcademicSession.objects.get_or_create(
                year=session_form.cleaned_data['year'], defaults={'created_by': request.user},
            )
            if institute.is_school_or_madrasah:
                institute.current_session = session
                institute.save(update_fields=['current_session'])
            return redirect('institute:onboarding_step3')
    else:
        dept_formset = OnboardingDepartmentFormSet(prefix='departments')
        session_form = OnboardingAcademicSessionForm(initial={'year': existing_session.year} if existing_session else None)

    ctx = {
        'dept_formset': dept_formset,
        'session_form': session_form,
        'existing_departments': existing_departments,
        'department_label': institute.department_label if institute else 'Department',
        **_onboarding_context(2),
    }
    return render(request, 'institute/onboarding/step2.html', ctx)


@login_required
def onboarding_step3(request):
    """Step 3: Load subjects from curriculum (optional)."""
    institute = _resolve_institute(request)
    if not institute:
        return redirect('institute:onboarding_step1')

    from django_school_management.curriculum.helpers import load_subjects_from_curriculum
    from django.contrib import messages

    load_result = None
    form = LoadSubjectsFromCurriculumForm(institute=institute)

    if request.method == 'POST':
        if 'load_subjects' in request.POST:
            form = LoadSubjectsFromCurriculumForm(request.POST, institute=institute)
            if form.is_valid():
                curriculum = form.cleaned_data['curriculum']
                class_numbers = form.get_class_numbers()
                if not class_numbers:
                    messages.warning(request, 'Please select at least one class range.')
                else:
                    load_result = load_subjects_from_curriculum(
                        institute, curriculum, class_numbers, request.user,
                    )
                    if load_result.get('errors'):
                        for err in load_result['errors']:
                            messages.warning(request, err)
                    created = load_result.get('subject_groups_created', 0)
                    if created or load_result.get('subjects_created') or load_result.get('semesters_created'):
                        institute.curriculum = curriculum
                        institute.save(update_fields=['curriculum'])
                        msg = (
                            f"Created {load_result.get('semesters_created', 0)} class(es), "
                            f"{load_result.get('subjects_created', 0)} subject(s), "
                            f"and {load_result.get('subject_groups_created', 0)} subject group(s)."
                        )
                        messages.success(request, msg)
        else:
            # Skip / Continue without loading
            return redirect('institute:onboarding_step4')

    ctx = {
        'form': form,
        'load_result': load_result,
        'department_label': institute.department_label if institute else 'Department',
        'semester_label': institute.semester_label if institute else 'Class',
        **_onboarding_context(3),
    }
    return render(request, 'institute/onboarding/step3_load_subjects.html', ctx)


@login_required
def onboarding_step4(request):
    """Step 4: Review and launch."""
    institute = _resolve_institute(request)
    if not institute:
        return redirect('institute:onboarding_step1')

    departments = Department.objects.filter(institute=institute)
    session = institute.current_session

    if request.method == 'POST':
        if institute.is_school_or_madrasah and session:
            institute.current_session = session
            institute.save(update_fields=['current_session'])
        institute.onboarding_completed = True
        institute.save(update_fields=['onboarding_completed'])
        request.session.pop('skip_onboarding', None)
        return redirect('index_view')

    ctx = {
        'institute': institute,
        'departments': departments,
        'session': session,
        'department_label': institute.department_label,
        **_onboarding_context(4),
    }
    return render(request, 'institute/onboarding/step4_review.html', ctx)
