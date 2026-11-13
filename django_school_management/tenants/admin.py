from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import Tenant, TenantDomain, BillingPlan


@admin.register(BillingPlan)
class BillingPlanAdmin(admin.ModelAdmin):
    """
    Admin interface for managing billing plans.
    
    Allows platform admins to create, edit, and manage subscription tiers.
    """
    
    list_display = [
        'name',
        'price_display',
        'billing_cycle',
        'max_students',
        'support_level',
        'is_active',
        'tenant_count'
    ]
    
    list_filter = [
        'billing_cycle',
        'support_level',
        'is_active',
        'is_recommended',
        'created_at'
    ]
    
    search_fields = ['name', 'slug', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'billing_cycle')
        }),
        ('Capacity Limits', {
            'fields': ('max_students', 'max_teachers', 'max_classes')
        }),
        ('Features & Support', {
            'fields': ('features', 'support_level')
        }),
        ('Status', {
            'fields': ('is_active', 'is_recommended')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    ordering = ['price']
    
    def price_display(self, obj):
        """Display price with formatting."""
        if obj.billing_cycle == 'trial':
            return format_html('<span style="color: green;">FREE</span>')
        return f"₦{obj.price:,.2f}"
    price_display.short_description = 'Price'
    
    def tenant_count(self, obj):
        """Display number of schools using this plan."""
        count = obj.tenants.count()
        return format_html(
            '<span style="background-color: #ddd; padding: 2px 6px; '
            'border-radius: 3px;">{}</span>',
            count
        )
    tenant_count.short_description = 'Schools'


class TenantDomainInline(admin.TabularInline):
    """
    Inline admin for managing domains within a Tenant.
    """
    
    model = TenantDomain
    extra = 1
    fields = ['domain', 'is_primary', 'verification_status', 'verified_at', 'is_active']
    readonly_fields = ['verification_status', 'verified_at']
    
    def verification_status(self, obj):
        """Display verification status with color coding."""
        colors = {
            'pending': '#FF9800',
            'verified': '#4CAF50',
            'failed': '#F44336',
            'expired': '#9C27B0'
        }
        color = colors.get(obj.verification_status, '#757575')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_verification_status_display()
        )
    verification_status.short_description = 'Status'


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """
    Admin interface for managing schools (tenants).
    
    Allows platform admins to onboard, manage, and monitor schools.
    """
    
    list_display = [
        'name',
        'subdomain_display',
        'status_display',
        'plan_display',
        'onboarding_progress',
        'created_date',
        'admin_user'
    ]
    
    list_filter = [
        'status',
        'billing_plan',
        'onboarding_completed',
        'created_at',
    ]
    
    search_fields = ['name', 'subdomain', 'slug']
    
    fieldsets = (
        ('School Information', {
            'fields': ('name', 'slug', 'subdomain', 'created_by')
        }),
        ('Onboarding', {
            'fields': (
                'status',
                'onboarding_completed',
                'onboarding_started_at',
                'onboarding_completed_at'
            ),
            'classes': ('collapse',)
        }),
        ('Billing', {
            'fields': ('billing_plan',)
        }),
        ('Branding', {
            'fields': ('logo', 'primary_color', 'secondary_color'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    inlines = [TenantDomainInline]
    
    ordering = ['-created_at']
    
    def subdomain_display(self, obj):
        """Display subdomain as a link."""
        return format_html(
            '<a href="http://{}.edunaija.local:8000/" target="_blank">{}</a>',
            obj.subdomain,
            obj.subdomain
        )
    subdomain_display.short_description = 'Subdomain'
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'onboarding_pending': '#FF9800',
            'onboarding_in_progress': '#2196F3',
            'onboarding_completed': '#4CAF50',
            'trial': '#2196F3',
            'active': '#4CAF50',
            'suspended': '#F44336',
            'archived': '#9E9E9E'
        }
        color = colors.get(obj.status, '#757575')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def plan_display(self, obj):
        """Display billing plan."""
        if obj.billing_plan:
            return f"{obj.billing_plan.name} ({obj.billing_plan.get_billing_cycle_display()})"
        return format_html('<span style="color: #999;">None</span>')
    plan_display.short_description = 'Plan'
    
    def onboarding_progress(self, obj):
        """Display onboarding completion progress."""
        if obj.onboarding_completed:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Complete</span>'
            )
        
        if obj.onboarding_started_at:
            days_since_start = (timezone.now() - obj.onboarding_started_at).days
            return format_html(
                '<span style="color: #FF9800;">In Progress ({} days)</span>',
                days_since_start
            )
        
        return format_html(
            '<span style="color: #999;">Pending</span>'
        )
    onboarding_progress.short_description = 'Onboarding'
    
    def created_date(self, obj):
        """Display creation date."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_date.short_description = 'Created'
    
    def admin_user(self, obj):
        """Display the user who created this tenant."""
        if obj.created_by:
            return format_html(
                '<strong>{}</strong> ({})',
                obj.created_by.get_full_name() or obj.created_by.username,
                obj.created_by.email
            )
        return format_html('<span style="color: #999;">—</span>')
    admin_user.short_description = 'Created By'
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        qs = super().get_queryset(request)
        return qs.select_related('billing_plan', 'created_by')
    
    actions = ['mark_active', 'mark_suspended', 'complete_onboarding']
    
    def mark_active(self, request, queryset):
        """Bulk action: Mark schools as active."""
        updated = queryset.exclude(status='active').update(
            status='active',
            onboarding_completed=True,
            onboarding_completed_at=timezone.now()
        )
        self.message_user(request, f'{updated} school(s) marked as active.')
    mark_active.short_description = 'Mark selected schools as active'
    
    def mark_suspended(self, request, queryset):
        """Bulk action: Suspend schools."""
        updated = queryset.exclude(status='suspended').update(status='suspended')
        self.message_user(request, f'{updated} school(s) suspended.')
    mark_suspended.short_description = 'Suspend selected schools'
    
    def complete_onboarding(self, request, queryset):
        """Bulk action: Complete onboarding for selected schools."""
        for tenant in queryset:
            if not tenant.onboarding_completed:
                tenant.complete_onboarding()
        self.message_user(request, f'{queryset.count()} school(s) onboarding marked complete.')
    complete_onboarding.short_description = 'Complete onboarding'


@admin.register(TenantDomain)
class TenantDomainAdmin(admin.ModelAdmin):
    """
    Admin interface for managing custom domains.
    
    Allows platform admins to verify and manage school domains.
    """
    
    list_display = [
        'domain',
        'tenant_name',
        'is_primary_display',
        'verification_status_display',
        'verified_at_display',
        'is_active_display'
    ]
    
    list_filter = [
        'verification_status',
        'is_primary',
        'is_active',
        'created_at',
        'verified_at'
    ]
    
    search_fields = ['domain', 'tenant__name', 'tenant__subdomain']
    
    fieldsets = (
        ('Domain Information', {
            'fields': ('tenant', 'domain', 'is_primary', 'is_active')
        }),
        ('Verification', {
            'fields': (
                'verification_status',
                'verification_method',
                'dns_challenge_token',
                'dns_challenge_type',
                'verified_at',
                'last_verification_check'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'dns_challenge_token',
        'verified_at',
        'last_verification_check'
    ]
    
    ordering = ['-created_at']
    
    def tenant_name(self, obj):
        """Display tenant name."""
        return format_html(
            '<strong>{}</strong> ({})',
            obj.tenant.name,
            obj.tenant.subdomain
        )
    tenant_name.short_description = 'School'
    
    def is_primary_display(self, obj):
        """Display primary domain indicator."""
        if obj.is_primary:
            return format_html(
                '<span style="background-color: #4CAF50; color: white; '
                'padding: 2px 6px; border-radius: 3px; font-weight: bold;">Primary</span>'
            )
        return '—'
    is_primary_display.short_description = 'Primary'
    
    def verification_status_display(self, obj):
        """Display verification status with color coding."""
        colors = {
            'pending': '#FF9800',
            'verified': '#4CAF50',
            'failed': '#F44336',
            'expired': '#9C27B0'
        }
        color = colors.get(obj.verification_status, '#757575')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_verification_status_display()
        )
    verification_status_display.short_description = 'Verification'
    
    def verified_at_display(self, obj):
        """Display verification timestamp."""
        if obj.verified_at:
            return obj.verified_at.strftime('%Y-%m-%d %H:%M')
        return '—'
    verified_at_display.short_description = 'Verified At'
    
    def is_active_display(self, obj):
        """Display active status."""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: #999;">Inactive</span>'
        )
    is_active_display.short_description = 'Status'
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        qs = super().get_queryset(request)
        return qs.select_related('tenant')
    
    actions = ['verify_domains', 'deactivate_domains']
    
    def verify_domains(self, request, queryset):
        """Bulk action: Trigger verification for selected domains."""
        from .services import verify_domain_ownership
        
        successful = 0
        failed = 0
        
        for domain in queryset:
            is_verified, message = verify_domain_ownership(domain)
            if is_verified:
                successful += 1
            else:
                failed += 1
        
        if successful:
            self.message_user(
                request,
                f'{successful} domain(s) verified successfully.'
            )
        if failed:
            self.message_user(
                request,
                f'{failed} domain(s) failed verification.',
                level='WARNING'
            )
    verify_domains.short_description = 'Verify selected domains'
    
    def deactivate_domains(self, request, queryset):
        """Bulk action: Deactivate domains."""
        updated = queryset.exclude(is_active=False).update(is_active=False)
        self.message_user(request, f'{updated} domain(s) deactivated.')
    deactivate_domains.short_description = 'Deactivate selected domains'
