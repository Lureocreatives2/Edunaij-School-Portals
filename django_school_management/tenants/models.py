from django.db import models
from django.conf import settings
from django.utils import timezone


class BillingPlan(models.Model):
    """
    Subscription plans available for schools on EduNaija.
    
    Defines pricing, features, and capacity limits for each tier.
    """
    
    BILLING_CYCLE_CHOICES = (
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
        ('trial', 'Trial (Free)'),
    )
    
    SUPPORT_LEVEL_CHOICES = (
        ('community', 'Community'),
        ('email', 'Email Support'),
        ('priority', 'Priority Support'),
        ('dedicated', 'Dedicated Account Manager'),
    )
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    billing_cycle = models.CharField(
        max_length=20, 
        choices=BILLING_CYCLE_CHOICES, 
        default='monthly'
    )
    
    # Features
    features = models.JSONField(
        default=dict, 
        blank=True,
        help_text='Feature flags as JSON'
    )
    
    # Capacity limits
    max_students = models.PositiveIntegerField(default=500)
    max_teachers = models.PositiveIntegerField(default=50)
    max_classes = models.PositiveIntegerField(default=20)
    
    # Support
    support_level = models.CharField(
        max_length=20, 
        choices=SUPPORT_LEVEL_CHOICES, 
        default='community'
    )
    
    # Admin flags
    is_active = models.BooleanField(default=True)
    is_recommended = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['price']
        verbose_name = 'Billing Plan'
        verbose_name_plural = 'Billing Plans'
    
    def __str__(self):
        return f"{self.name} - {self.get_billing_cycle_display()}"


class Tenant(models.Model):
    STATUS_CHOICES = (
        ('onboarding_pending', 'Onboarding Pending'),
        ('onboarding_in_progress', 'Onboarding In Progress'),
        ('onboarding_completed', 'Onboarding Completed'),
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('archived', 'Archived'),
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=120, unique=True)
    subdomain = models.CharField(max_length=80, unique=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='onboarding_pending')
    onboarding_completed = models.BooleanField(default=False)
    
    # Onboarding tracking
    onboarding_started_at = models.DateTimeField(null=True, blank=True)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Billing
    billing_plan = models.ForeignKey(
        BillingPlan,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tenants',
        help_text='Subscription plan for this school'
    )
    
    # Branding
    logo = models.ImageField(upload_to='tenants/logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=20, blank=True, default='#0f172a')
    secondary_color = models.CharField(max_length=20, blank=True, default='#2563eb')
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tenants',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['subdomain']),
        ]

    def __str__(self):
        return self.name
    
    @property
    def assigned_email(self):
        if self.pk and settings.SCHOOL_EMAIL_DOMAIN:
            return f'school-{self.pk}@{settings.SCHOOL_EMAIL_DOMAIN}'
        return ''

    def start_onboarding(self):
        """Mark onboarding as started."""
        if not self.onboarding_started_at:
            self.onboarding_started_at = timezone.now()
            self.status = 'onboarding_in_progress'
            self.save()
    
    def complete_onboarding(self):
        """Mark onboarding as complete."""
        self.onboarding_completed = True
        self.onboarding_completed_at = timezone.now()
        self.status = 'active'
        self.save()


class TenantDomain(models.Model):
    """
    Custom domains for schools on EduNaija.
    
    Allows schools to use custom domains (e.g., school.edu.ng) in addition to subdomains.
    """
    
    VERIFICATION_STATUS_CHOICES = (
        ('pending', 'Verification Pending'),
        ('verified', 'Verified'),
        ('failed', 'Verification Failed'),
        ('expired', 'Verification Expired'),
    )
    
    VERIFICATION_METHOD_CHOICES = (
        ('cname', 'CNAME Record'),
        ('txt', 'TXT Record'),
        ('auto', 'Automatic'),
    )
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='domains')
    domain = models.CharField(max_length=255, unique=True)
    is_primary = models.BooleanField(default=False, help_text='Primary domain for this school')
    is_active = models.BooleanField(default=True)
    
    # Verification
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending'
    )
    verification_method = models.CharField(
        max_length=20,
        choices=VERIFICATION_METHOD_CHOICES,
        default='cname'
    )
    dns_challenge_token = models.CharField(max_length=255, blank=True)
    dns_challenge_type = models.CharField(max_length=20, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    last_verification_check = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['domain']
        indexes = [
            models.Index(fields=['tenant', 'is_primary']),
            models.Index(fields=['domain']),
            models.Index(fields=['verification_status']),
        ]

    def __str__(self):
        return f'{self.domain} -> {self.tenant}'
    
    def is_verified(self):
        """Check if domain is verified."""
        return self.verification_status == 'verified'
