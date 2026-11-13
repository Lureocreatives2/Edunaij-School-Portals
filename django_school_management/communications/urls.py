from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    path('announcements/', views.announcements_list, name='announcements_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
]
