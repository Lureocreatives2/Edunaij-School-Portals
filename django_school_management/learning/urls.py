from django.urls import path
from . import views

app_name = 'learning'

urlpatterns = [
    path('teacher/assignments/create/', views.create_assignment, name='create_assignment'),
    path('assignments/', views.student_assignments, name='student_assignments'),
    path('assignments/<int:assignment_id>/submit/', views.submit_assignment, name='submit_assignment'),
    path('teacher/assignments/', views.teacher_assignments, name='teacher_assignments'),
    path('teacher/submission/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),
]
