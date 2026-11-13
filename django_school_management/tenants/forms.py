from django import forms
from django.utils.text import slugify
from django.core.exceptions import ValidationError
import re

from .models import Tenant, TenantDomain, BillingPlan


class SchoolOnboardingForm(forms.ModelForm):
    """
    Form for platform admins to onboard a new school.
    
    Handles:
    - School name validation
    - Subdomain uniqueness and format
    - Plan selection
    - Optional custom domain
    """
    
    plan = forms.ModelChoiceField(
        queryset=BillingPlan.objects.filter(is_active=True),
        required=True,
        label='Billing Plan',
        empty_label='Select a plan'
    )
    
    custom_domain = forms.CharField(
        required=False,
        label='Custom Domain (optional)',
        help_text='e.g., myschool.edu.ng',
        widget=forms.TextInput(attrs={'placeholder': 'myschool.edu.ng'})
    )
    
    class Meta:
        model = Tenant
        fields = ['name', 'subdomain', 'primary_color', 'secondary_color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'School Name'
            }),
            'subdomain': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'unique-subdomain',
                'help_text': 'Lowercase, alphanumeric and dashes only'
            }),
            'primary_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control'
            }),
            'secondary_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control'
            }),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('School name is required.')
        if len(name) < 2:
            raise ValidationError('School name must be at least 2 characters.')
        if len(name) > 255:
            raise ValidationError('School name is too long.')
        return name
    
    def clean_subdomain(self):
        subdomain = self.cleaned_data.get('subdomain', '').strip().lower()
        
        if not subdomain:
            raise ValidationError('Subdomain is required.')
        
        # Validate format: lowercase, alphanumeric, dashes
        if not re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', subdomain):
            raise ValidationError(
                'Subdomain must start with a letter or number, contain only lowercase '
                'letters, numbers, and dashes, and not end with a dash.'
            )
        
        # Check uniqueness
        if Tenant.objects.filter(subdomain=subdomain).exists():
            raise ValidationError(f'The subdomain "{subdomain}" is already taken.')
        
        if len(subdomain) < 3:
            raise ValidationError('Subdomain must be at least 3 characters.')
        if len(subdomain) > 63:
            raise ValidationError('Subdomain must not exceed 63 characters.')
        
        return subdomain
    
    def clean_custom_domain(self):
        custom_domain = self.cleaned_data.get('custom_domain', '').strip().lower()
        
        if not custom_domain:
            return None
        
        # Basic domain validation
        if not re.match(
            r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$',
            custom_domain
        ):
            raise ValidationError('Invalid domain format. Please enter a valid domain.')
        
        # Check uniqueness in TenantDomain
        if TenantDomain.objects.filter(domain=custom_domain).exists():
            raise ValidationError(f'The domain "{custom_domain}" is already registered.')
        
        return custom_domain
    
    def clean(self):
        cleaned_data = super().clean()
        plan = cleaned_data.get('plan')
        
        if not plan:
            raise ValidationError('Please select a billing plan.')
        
        return cleaned_data
    
    def save(self, commit=True, user=None):
        """
        Save the tenant with plan and optional custom domain.
        
        Args:
            commit: Whether to save to database
            user: The user creating the tenant (for audit trail)
        """
        instance = super().save(commit=False)
        
        # Set status and plan
        instance.status = 'onboarding_in_progress'
        instance.billing_plan = self.cleaned_data['plan']
        instance.slug = slugify(instance.name)
        instance.created_by = user
        
        if commit:
            instance.save()
            instance.start_onboarding()
            
            # Create custom domain if provided
            custom_domain = self.cleaned_data.get('custom_domain')
            if custom_domain:
                TenantDomain.objects.create(
                    tenant=instance,
                    domain=custom_domain,
                    is_primary=False,
                    verification_status='pending'
                )
        
        return instance


class SchoolEditForm(forms.ModelForm):
    """
    Form for editing school details (name, branding).
    
    Does not allow changing subdomain or plan (for data integrity).
    """
    
    class Meta:
        model = Tenant
        fields = ['name', 'primary_color', 'secondary_color', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('School name is required.')
        if len(name) < 2:
            raise ValidationError('School name must be at least 2 characters.')
        return name


class CustomDomainRegistrationForm(forms.ModelForm):
    """
    Form for schools to register custom domains.
    
    Validates domain format and uniqueness.
    """
    
    class Meta:
        model = TenantDomain
        fields = ['domain']
        widgets = {
            'domain': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'myschool.edu.ng'
            })
        }
    
    def clean_domain(self):
        domain = self.cleaned_data.get('domain', '').strip().lower()
        
        if not domain:
            raise ValidationError('Domain is required.')
        
        # Validate format
        if not re.match(
            r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$',
            domain
        ):
            raise ValidationError('Invalid domain format.')
        
        # Check uniqueness
        if TenantDomain.objects.filter(domain=domain).exists():
            raise ValidationError(f'The domain "{domain}" is already registered.')
        
        return domain
    
    def save(self, tenant, commit=True):
        """
        Save custom domain for a tenant.
        
        Args:
            tenant: The Tenant instance
            commit: Whether to save to database
        """
        instance = super().save(commit=False)
        instance.tenant = tenant
        instance.verification_status = 'pending'
        instance.verification_method = 'cname'
        
        if commit:
            instance.save()
        
        return instance
