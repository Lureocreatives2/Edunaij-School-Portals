from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from .models import Announcement, Notification
from django_school_management.parents.models import Guardian

@login_required
def announcements_list(request):
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        return HttpResponseForbidden("Tenant context missing.")

    # Determine user role to filter announcements
    user_roles = ['all']
    if request.user.is_staff or hasattr(request.user, 'teacher_profile'):
        user_roles.append('teachers')
    if hasattr(request.user, 'guardian_profile'):
        user_roles.append('parents')
    if hasattr(request.user, 'student'):
        user_roles.append('students')

    announcements = Announcement.objects.filter(
        tenant=tenant,
        target_audience__in=user_roles
    )

    unread_notifications_count = Notification.objects.filter(
        tenant=tenant, recipient=request.user, is_read=False
    ).count()

    context = {
        'announcements': announcements,
        'tenant': tenant,
        'unread_count': unread_notifications_count
    }
    return render(request, 'communications/announcements.html', context)

@login_required
def mark_notification_read(request, notification_id):
    tenant = getattr(request, 'tenant', None)
    notification = get_object_or_404(Notification, id=notification_id, tenant=tenant, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    if notification.link:
        return redirect(notification.link)
    return redirect('communications:announcements_list')
