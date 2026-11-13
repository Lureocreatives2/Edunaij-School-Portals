from django_countries.fields import CountryField

from django_prometheus.models import ExportModelOperationsMixin

from django.db import models
from django.db.models.signals import pre_save
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.urls import reverse

from .utils import model_help_texts


class User(ExportModelOperationsMixin('user'), AbstractUser):
    REQUESTED_ACCOUNT_TYPE_CHOICES = (
        ('subscriber', 'Subscriber'),
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('editor', 'Editor'),
        ('academic_officer', 'Academic Officer'),
        ('admin', 'Admin'),
    )
    APPROVAL_CHOICES = (
        ('n', 'Not Requested For Approval'),
        ('p', 'Approval Application is Pending'),
        ('d', 'Approval Request Declined'),
        ('a', 'Verified')
    )
    approval_status = models.CharField(
        max_length=2,
        choices=APPROVAL_CHOICES,
        default='n',
    )
    employee_or_student_id = models.CharField(
        max_length=10,
        blank=True, null=True
    )
    requested_role = models.CharField(
        choices=REQUESTED_ACCOUNT_TYPE_CHOICES,
        max_length=50,
        default=REQUESTED_ACCOUNT_TYPE_CHOICES[0][0]
    )
    approval_extra_note = models.TextField(
        blank=True, null=True
    )
    institute = models.ForeignKey(
        'institute.InstituteProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='users',
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='users',
    )

    @property
    def assigned_school_email(self):
        official_roles = {'admin', 'teacher', 'academic_officer', 'editor'}
        if (self.pk and self.tenant_id and self.institute_id and self.is_active
                and not self.is_superuser and self.approval_status == 'a'
                and self.requested_role in official_roles and settings.SCHOOL_EMAIL_DOMAIN):
            return f'official-{self.tenant_id}-{self.pk}@{settings.SCHOOL_EMAIL_DOMAIN}'
        return ''

    def get_author_url(self):
        return reverse(
            'articles:author_profile',
            args=[self.username,])

    def can_access_tenant(self, tenant_obj=None):
        if not tenant_obj:
            return True
        if self.is_superuser:
            return True
        if not self.is_authenticated:
            return False
        return self.tenant_id == tenant_obj.pk


class CustomGroup(ExportModelOperationsMixin('custom_group'), Group):
    group_creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE)

    def display_group(self):
        return f'{self.name} created by {self.group_creator}'


class SocialLink(ExportModelOperationsMixin('social_link'), models.Model):
    user_profile = models.ForeignKey(
        'CommonUserProfile',
        on_delete=models.CASCADE
    )
    media_name = models.CharField(
        max_length=50
    )
    url = models.URLField()

    def __str__(self):
        return self.media_name


class CommonUserProfile(ExportModelOperationsMixin('common_user_profile'), models.Model):
    """Core details of user profile created only after account verification by institute."""
    user = models.OneToOneField(
        User,
        related_name='profile',
        on_delete=models.SET_NULL,
        null=True
    )
    profile_picture = models.ImageField(
        upload_to='profile-pictures',
        blank=True,
        null=True
    )
    cover_picture = models.ImageField(
        upload_to='cover-pictures',
        blank=True,
        null=True
    )
    headline = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    show_headline_in_bio = models.BooleanField(
        help_text=model_help_texts.COMMON_USER_PROFILE_SHOW_HEADLINE_IN_BIO_TEXT,
        default=False
    )
    summary = models.TextField(
        help_text=model_help_texts.COMMON_USER_PROFILE_SUMMARY_TEXT,
        blank=True,
        null=True
    )
    country = CountryField(
        blank=True,
        null=True
    )
    social_links = models.ManyToManyField(
        SocialLink,
        related_name='social_links',
        blank=True
    )

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'{self.user}\'s profile'


class AuditLog(models.Model):
    """
    Audit log entry for sensitive operations.
    
    Records who did what, when, and from which tenant context.
    """
    
    OPERATION_CHOICES = (
        ('login', 'User Login'),
        ('login_failed', 'Failed Login Attempt'),
        ('logout', 'User Logout'),
        ('password_change', 'Password Changed'),
        ('role_assign', 'Role Assigned'),
        ('role_remove', 'Role Removed'),
        ('tenant_create', 'Tenant Created'),
        ('tenant_update', 'Tenant Updated'),
        ('tenant_status_change', 'Tenant Status Changed'),
        ('user_create', 'User Created'),
        ('user_update', 'User Updated'),
        ('user_delete', 'User Deleted'),
        ('permission_grant', 'Permission Granted'),
        ('permission_revoke', 'Permission Revoked'),
        ('payment_process', 'Payment Processed'),
        ('export_data', 'Data Exported'),
        ('admin_access', 'Admin Access'),
        ('admin_action', 'Admin Action'),
    )
    
    # Audit event details
    operation = models.CharField(max_length=50, choices=OPERATION_CHOICES)
    actor = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs_as_actor',
        help_text='User who performed the action'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        help_text='Tenant context for the action'
    )
    
    # Target resource
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text='Type of object affected'
    )
    object_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='ID of object affected'
    )
    
    # Details
    description = models.TextField(
        blank=True,
        help_text='Human-readable description of the action'
    )
    details = models.JSONField(
        default=dict, blank=True,
        help_text='Additional metadata as JSON'
    )
    
    # Request context
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        help_text='IP address of the request'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='Browser user agent string'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['actor', '-created_at']),
            models.Index(fields=['operation', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_operation_display()} by {self.actor} at {self.created_at}"

