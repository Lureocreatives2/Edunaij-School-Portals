from django.urls import path
from . import views

app_name = 'parents'

urlpatterns = [
    path('students/<int:student_id>/', views.child_progress, name='child_progress'),
    path('dashboard/', views.parent_dashboard, name='parent_dashboard'),
]
