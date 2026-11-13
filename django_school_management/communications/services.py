from .models import Notification
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @classmethod
    def create_in_app_notification(cls, tenant, user, title, message, link=None):
        """Creates an in-app notification strictly scoped to the tenant."""
        Notification.objects.create(
            tenant=tenant,
            recipient=user,
            title=title,
            message=message,
            link=link
        )

    @classmethod
    def send_email_alert(cls, recipient_email, subject, message):
        """Sends an automated email (e.g., for fee reminders or critical announcements)."""
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            return False
