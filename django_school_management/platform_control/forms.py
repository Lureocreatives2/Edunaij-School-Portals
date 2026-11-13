import re

from django import forms
from django_school_management.tenants.models import Tenant, BillingPlan
from .models import ApplicationRelease, SchoolRegistration


class SchoolControlForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['billing_plan', 'status']
        help_texts = {'billing_plan': 'Changing a plan updates school configuration. It does not charge a payment method.'}


class ReleaseForm(forms.ModelForm):
    class Meta:
        model = ApplicationRelease
        fields = ['version', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 8})}


class PlanForm(forms.ModelForm):
    class Meta:
        model = BillingPlan
        fields = ['name', 'slug', 'description', 'price', 'billing_cycle', 'max_students', 'max_teachers', 'max_classes', 'is_active']

    def clean_price(self):
        value = self.cleaned_data['price']
        if value < 0:
            raise forms.ValidationError('Price cannot be negative.')
        return value


NIGERIAN_STATES = (
    'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue', 'Borno',
    'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'FCT', 'Gombe', 'Imo',
    'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos',
    'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 'Sokoto',
    'Taraba', 'Yobe', 'Zamfara',
)


class SchoolRegistrationForm(forms.ModelForm):
    state = forms.ChoiceField(label='State or FCT', choices=[('', 'Select state or FCT'), *(
        (state, state) for state in NIGERIAN_STATES
    )])
    contact_phone = forms.CharField(max_length=32, widget=forms.TextInput(
        attrs={'type': 'tel', 'autocomplete': 'tel', 'placeholder': '+234 803 000 0000'},
    ))
    sections = (
        ('School details', ('school_name', 'school_type', 'ownership', 'state', 'lga', 'campus_address')),
        ('Authorised contact', ('contact_name', 'contact_role', 'contact_email', 'contact_phone')),
        ('Registration and approval', ('cac_status', 'cac_legal_name', 'cac_number', 'approval_status',
                                       'approval_authority', 'approval_reference', 'school_code')),
    )

    class Meta:
        model = SchoolRegistration
        fields = [
            'school_name', 'school_type', 'ownership', 'state', 'lga', 'campus_address',
            'contact_name', 'contact_role', 'contact_email', 'contact_phone',
            'cac_status', 'cac_legal_name', 'cac_number', 'approval_status',
            'approval_authority', 'approval_reference', 'school_code',
        ]
        help_texts = {
            'cac_status': 'Private schools and other non-state operators only.',
            'cac_number': 'Enter the reference as printed on the certificate, including any prefix.',
            'approval_authority': 'For example, Lagos State Office of Education Quality Assurance.',
            'school_code': 'Optional. Use the code assigned by your education authority, if available.',
        }
        widgets = {
            'school_name': forms.TextInput(attrs={'autocomplete': 'organization'}),
            'campus_address': forms.TextInput(attrs={'autocomplete': 'street-address'}),
            'contact_name': forms.TextInput(attrs={'autocomplete': 'name'}),
            'contact_role': forms.TextInput(attrs={'autocomplete': 'organization-title'}),
            'contact_email': forms.EmailInput(attrs={'autocomplete': 'email'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('ownership', 'lga', 'campus_address', 'contact_role', 'contact_phone'):
            self.fields[name].required = True

    def grouped_fields(self):
        return [(label, [self[name] for name in names]) for label, names in self.sections]

    def clean_contact_email(self):
        return self.cleaned_data['contact_email'].lower()

    def clean_contact_phone(self):
        phone = re.sub(r'[\s()-]', '', self.cleaned_data['contact_phone'])
        if phone.startswith('0'):
            phone = '+234' + phone[1:]
        elif phone.startswith('234'):
            phone = '+' + phone
        if not re.fullmatch(r'\+234[1-9][0-9]{9}', phone):
            raise forms.ValidationError('Enter a Nigerian number starting with 0 or +234.')
        return phone

    def clean(self):
        data = super().clean()
        if data.get('ownership') == SchoolRegistration.Ownership.PRIVATE:
            if not data.get('cac_status'):
                self.add_error('cac_status', 'Select the current CAC registration status.')
            if not data.get('approval_status'):
                self.add_error('approval_status', 'Select the current education approval status.')
        if data.get('cac_status') == SchoolRegistration.CACStatus.REGISTERED:
            for name in ('cac_legal_name', 'cac_number'):
                if not data.get(name):
                    self.add_error(name, 'Enter this detail from the CAC certificate.')
        if data.get('approval_status') == SchoolRegistration.ApprovalStatus.APPROVED:
            for name in ('approval_authority', 'approval_reference'):
                if not data.get(name):
                    self.add_error(name, 'Enter this detail from the education approval letter.')
        return data

    def validate_constraints(self):
        # The submit view handles duplicate requests without revealing an earlier submission.
        pass
