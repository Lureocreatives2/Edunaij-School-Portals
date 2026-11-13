from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_safe, require_http_methods
from django.views.decorators.cache import never_cache
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from allauth.core import ratelimit
from django_school_management.tenants.models import Tenant, BillingPlan
from django_school_management.billing.models import Subscription
from django_school_management.tenants.scoping import request_institute
from .models import ApplicationRelease, PlatformAction, SchoolRegistration
from .forms import SchoolControlForm, ReleaseForm, PlanForm, SchoolRegistrationForm
import logging
logger = logging.getLogger(__name__)


def platform_owner(view):
    @never_cache
    @login_required(login_url='platform:login')
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not request.user.is_superuser or not request.user.is_active:
            raise PermissionDenied('Platform owner access is required.')
        return view(request, *args, **kwargs)
    return guarded


@platform_owner
def overview(request):
    schools = Tenant.objects.select_related('billing_plan', 'subscription').order_by('name')
    return render(request, 'platform/overview.html', {
        'platform_mode': True, 'schools': schools,
        'school_count': schools.count(),
        'active_count': schools.filter(status__in=['active', 'trial']).count(),
        'suspended_count': schools.filter(status='suspended').count(),
        'subscription_count': Subscription.objects.filter(status='active').count(),
    })


@platform_owner
def school_detail(request, pk):
    school = get_object_or_404(Tenant, pk=pk)
    before = {'status': school.status, 'billing_plan_id': school.billing_plan_id}
    form = SchoolControlForm(request.POST or None, instance=school)
    if request.method == 'POST' and form.is_valid():
        changes = list(form.changed_data)
        with transaction.atomic():
            form.save()
            PlatformAction.objects.create(actor=request.user, action='school_configuration', target=str(school.pk),
                details={'before': before, 'after': {'status': school.status, 'billing_plan_id': school.billing_plan_id}})
        logger.warning('Platform school configuration changed: actor=%s tenant=%s fields=%s', request.user.pk, school.pk, changes)
        messages.success(request, 'School configuration saved. No payment was charged.')
        return redirect('platform:school', pk=pk)
    return render(request, 'platform/school.html', {'platform_mode': True, 'school': school,
        'form': form, 'subscription': Subscription.objects.filter(tenant=school).first()},
        status=400 if request.method == 'POST' else 200)


@platform_owner
def releases(request):
    form = ReleaseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        release = form.save(commit=False)
        release.created_by = request.user
        with transaction.atomic():
            release.save()
            PlatformAction.objects.create(actor=request.user, action='release_draft', target=release.version)
        messages.success(request, 'Release draft created.')
        return redirect('platform:releases')
    return render(request, 'platform/releases.html', {'platform_mode': True, 'form': form,
        'releases': ApplicationRelease.objects.all()}, status=400 if request.method == 'POST' else 200)


@platform_owner
@require_POST
def publish_release(request, pk):
    with transaction.atomic():
        release = get_object_or_404(ApplicationRelease.objects.select_for_update(), pk=pk)
        if not release.published_at:
            release.published_at = timezone.now()
            release.save(update_fields=['published_at'])
            PlatformAction.objects.create(actor=request.user, action='release_published', target=release.version)
            logger.warning('Platform release announced: actor=%s release=%s', request.user.pk, release.pk)
    messages.success(request, 'Release notes published to school workspaces. Application code was not deployed.')
    return redirect('platform:releases')


@login_required(login_url='account_login')
def release_notes(request, pk):
    if not request.user.is_superuser:
        request_institute(request)
    release = get_object_or_404(ApplicationRelease, pk=pk, published_at__isnull=False)
    return render(request, 'platform/notes.html', {'platform_mode': request.user.is_superuser, 'release': release})


@platform_owner
def plans(request):
    form = PlanForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            plan = form.save()
            PlatformAction.objects.create(actor=request.user, action='plan_created', target=str(plan.pk))
        messages.success(request, 'Subscription plan created. No payment was charged.')
        return redirect('platform:plans')
    return render(request, 'platform/plans.html', {'platform_mode': True, 'form': form,
        'plans': BillingPlan.objects.all()}, status=400 if request.method == 'POST' else 200)


@never_cache
@require_http_methods(['GET', 'HEAD', 'POST'])
def register_school(request):
    if request.method == 'POST':
        limited = ratelimit.consume_or_429(request, action='school_registration')
        if limited is not None:
            return limited
        form = SchoolRegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            SchoolRegistration.objects.get_or_create(
                school_name=data.pop('school_name'), contact_email=data.pop('contact_email'), defaults=data,
            )
            return redirect('platform:registration_received')
    else:
        form = SchoolRegistrationForm()
    return render(request, 'platform/register.html', {'form': form},
                  status=400 if request.method == 'POST' else 200)


@require_safe
def registration_received(request):
    return render(request, 'platform/register.html', {'received': True})


@platform_owner
@require_safe
def school_registrations(request):
    requests = Paginator(SchoolRegistration.objects.all(), 25).get_page(request.GET.get('page'))
    return render(request, 'platform/registrations.html', {'platform_mode': True, 'registrations': requests})
