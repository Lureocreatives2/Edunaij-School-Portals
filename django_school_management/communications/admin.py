from django.contrib import admin
from .models import Announcement, Notification

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenant', 'target_audience', 'is_pinned', 'created_at')
    list_filter = ('tenant', 'target_audience', 'is_pinned')
    search_fields = ('title', 'message')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'tenant', 'is_read', 'created_at')
    list_filter = ('is_read', 'tenant')
    search_fields = ('title', 'message', 'recipient__username')
