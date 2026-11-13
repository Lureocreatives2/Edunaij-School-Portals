from django.http import HttpResponseNotFound
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic import UpdateView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

from .models import Teacher, Designation
from .forms import TeacherForm, TeacherDesignationForm
from permission_handlers.administrative import (
    user_editor_admin_or_su,
    user_is_admin_or_su,
    user_is_teacher_or_administrative,
)
from permission_handlers.basic import user_is_teacher, user_is_verified
from django_school_management.mixins.no_permission import LoginRequiredNoPermissionMixin
from django_school_management.mixins.institute import get_user_institute, InstituteScopedQuerysetMixin
from django_school_management.tenants.scoping import request_institute
from django.views.decorators.http import require_POST


@user_passes_test(user_is_teacher_or_administrative)
def teachers_view(request):
    """
    :param request:
    :return: list of teachers to logged in user, login form instead.
    """
    institute = request_institute(request)
    teachers = Teacher.objects.filter(institute=institute) if institute else Teacher.objects.none()
    context = {'teachers': teachers}
    return render(request, 'teachers/teacher_list.html', context)


# TODO: Reduce duplicate queries.
@user_passes_test(user_is_admin_or_su)
def add_teacher_view(request):
    """
    :param request:
    :return: teacher add form
    """
    if request.method == 'POST':
        form = TeacherForm(request.POST, request.FILES)
        if form.is_valid():
            teacher = form.save(commit=False)
            teacher.institute = request_institute(request)
            teacher.created_by = request.user
            teacher.save()
            form.save_m2m()
            return redirect('teachers:all_teacher')
        context = {'form': form}
        return render(request, 'teachers/add_teacher.html', context)
    form = TeacherForm()
    context = {'form': form}
    return render(request, 'teachers/add_teacher.html', context)


@user_passes_test(user_is_verified)
def teacher_detail_view(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk, institute=request_institute(request))
    context = {'teacher': teacher}
    return render(request, 'teachers/teacher_detail.html', context)


class teacher_update_view(InstituteScopedQuerysetMixin, LoginRequiredNoPermissionMixin, UserPassesTestMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm

    def form_valid(self, form):
        form.instance.institute = request_institute(self.request)
        return super().form_valid(form)
    template_name = 'teachers/update_teacher.html'

    def test_func(self):
        user = self.request.user
        return user_editor_admin_or_su(user)

    def get_success_url(self):
        teacher_id = self.kwargs['pk']
        return reverse_lazy('teachers:teacher_details', kwargs={'pk': teacher_id})


@user_passes_test(user_is_admin_or_su)
@require_POST
def teacher_delete_view(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk, institute=request_institute(request))
    teacher.delete()
    return redirect('teachers:all_teacher')


@user_passes_test(user_is_admin_or_su)
def create_designation(request):
    if request.method == 'POST':
        form = TeacherDesignationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('teachers:designations')
    else:
        form = TeacherDesignationForm()
    context = {'form': form}
    return render(request, 'teachers/designation_create.html', context)


class designation_list_view(LoginRequiredNoPermissionMixin, UserPassesTestMixin, ListView):
    model = Designation
    template_name = 'teachers/designation_list.html'

    def test_func(self):
        user = self.request.user
        return user_is_verified(user)


@user_passes_test(user_is_teacher)
def teacher_my_portal(request, teacher_id: str):
    teacher = get_object_or_404(Teacher, user=request.user, employee_id=teacher_id, institute=request_institute(request))
    ctx = {'teacher': teacher}
    return render(request, "teachers/my-portal.html", ctx)