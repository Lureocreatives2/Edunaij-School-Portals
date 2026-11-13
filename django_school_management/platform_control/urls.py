from django.urls import path
from allauth.account.views import LoginView
from . import views
app_name = 'platform'
urlpatterns = [
    path('register/', views.register_school, name='register_school'),
    path('register/received/', views.registration_received, name='registration_received'),
    path('registrations/', views.school_registrations, name='school_registrations'),
    path('plans/', views.plans, name='plans'),
    path('', views.overview, name='overview'),
    path('login/', LoginView.as_view(template_name='platform/login.html'), name='login'),
    path('schools/<int:pk>/', views.school_detail, name='school'),
    path('releases/', views.releases, name='releases'),
    path('releases/<int:pk>/publish/', views.publish_release, name='publish_release'),
    path('releases/<int:pk>/notes/', views.release_notes, name='release_notes'),
]
