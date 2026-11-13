from django import forms
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from .models import Assignment, Submission


def validate_attachment(file):
    if file is None:
        return
    FileExtensionValidator(['pdf', 'docx', 'odt', 'txt', 'png', 'jpg', 'jpeg', 'webp'])(file)
    if file.size > 10 * 1024 * 1024:
        raise forms.ValidationError('The maximum file size is 10 MB.')


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'academic_class', 'due_date', 'attachment']
        widgets = {'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')}

    def __init__(self, *args, teacher, tenant, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.teacher = teacher
        self.instance.tenant = tenant
        self.fields['academic_class'].queryset = self.fields['academic_class'].queryset.filter(is_active=True, institutes_offering__tenant=tenant)

    def clean_due_date(self):
        value = self.cleaned_data['due_date']
        if value <= timezone.now():
            raise forms.ValidationError('Choose a future due date.')
        return value

    def clean_attachment(self):
        file = self.cleaned_data.get('attachment')
        validate_attachment(file)
        return file


class SubmissionForm(forms.Form):
    text_response = forms.CharField(required=False, max_length=20000, widget=forms.Textarea)
    file = forms.FileField(required=False, validators=[validate_attachment])

    def clean(self):
        data = super().clean()
        if not data.get('text_response') and not data.get('file'):
            raise forms.ValidationError('Add an answer or attach a file.')
        return data


class GradeForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['grade', 'feedback']
        widgets = {'feedback': forms.Textarea(attrs={'rows': 3})}
