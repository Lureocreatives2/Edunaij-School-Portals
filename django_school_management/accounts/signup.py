from django import forms
from allauth.account.forms import SignupForm
from django_school_management.tenants.scoping import request_institute


class SchoolSignupForm(SignupForm):
    def save(self, request):
        # Resolve the school before creating an account; never infer it from submitted IDs.
        school = request_institute(request)
        user = super().save(request)
        user.tenant = request.tenant
        user.institute = school
        user.is_staff = False
        user.is_superuser = False
        user.approval_status = 'n'
        user.requested_role = 'subscriber'
        user.save(update_fields=['tenant', 'institute', 'is_staff', 'is_superuser',
                                 'approval_status', 'requested_role'])
        return user
