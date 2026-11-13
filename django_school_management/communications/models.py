from django.db import models
from django.conf import settings

class Announcement(models.Model):
    """School-wide or targeted broadcasts from Admins/Teachers."""
    TARGET_CHOICES = [
        ('all', 'Entire School'),
        ('teachers', 'Teachers Only'),
        ('parents', 'Parents Only'),
        ('students', 'Students Only'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='announcements')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    target_audience = models.CharField(max_length=20, choices=TARGET_CHOICES, default='all')
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.tenant.name})"


class Notification(models.Model):
    """In-app notifications for automated alerts (grades, fees, etc.)."""
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.URLField(blank=True, null=True, help_text="Optional URL to redirect to when clicked")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"
