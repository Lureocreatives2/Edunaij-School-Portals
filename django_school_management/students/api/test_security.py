from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import SimpleTestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser
from .views import SchoolStaffScopeMixin, StudentViewSet, AdmissionStudentViewSet


class QueryBase:
    def get_queryset(self):
        return self.queryset


class ScopedView(SchoolStaffScopeMixin, QueryBase):
    pass


class SchoolScopeTests(SimpleTestCase):
    def test_missing_school_fails_closed(self):
        view = ScopedView()
        view.request = SimpleNamespace(user=SimpleNamespace(institute_id=None))
        view.queryset = Mock()
        with self.assertRaises(PermissionDenied):
            view.get_queryset()

    @patch('django_school_management.tenants.scoping.request_institute')
    def test_query_uses_authenticated_school(self, resolve):
        resolve.return_value = SimpleNamespace(pk=42)
        view = ScopedView()
        view.request = SimpleNamespace(user=SimpleNamespace(institute_id=42))
        view.queryset = Mock()
        view.get_queryset()
        view.queryset.filter.assert_called_once_with(department_choice__institute_id=42)

    def test_administrative_endpoints_require_staff(self):
        request = SimpleNamespace(user=SimpleNamespace(is_staff=False))
        for view_type in (StudentViewSet, AdmissionStudentViewSet):
            view = view_type()
            view.action = 'list'
            self.assertTrue(any(isinstance(p, IsAdminUser) for p in view.get_permissions()))
            self.assertFalse(all(p.has_permission(request, view) for p in view.get_permissions()))
