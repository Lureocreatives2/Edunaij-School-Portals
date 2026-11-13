from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('analytics/', views.school_analytics_dashboard, name='analytics_dashboard'),
    path('report-card/<int:student_id>/pdf/', views.generate_report_card_pdf, name='report_card_pdf'),
]
