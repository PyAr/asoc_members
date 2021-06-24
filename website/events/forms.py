from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from stdnum.ar import cbu

from events.models import (
    BankAccountData,
    Event,
    Invoice,
    InvoiceAffect,
    Organizer,
    OrganizerRefund,
    Payment,
    Provider,
    ProviderExpense,
    Sponsor,
    SponsorCategory,
    Sponsoring
)


def validate_cbu(cbu_number, form):
    if not cbu_number.isdigit():
        form._errors["cbu"] = form.error_class(['El CBU tiene que tener sólo dígitos'])
    elif len(cbu_number) != 22:
        form._errors["cbu"] = form.error_class(['El CBU tiene que tener 22 dígitos'])
    elif not cbu.is_valid(cbu_number):
        form._errors["cbu"] = form.error_class(['El CBU especificado no es un CBU válido'])


class OrganizerUserSignupForm(UserCreationForm):
    email = forms.EmailField(label=_('Correo Electrónico'), max_length=200, help_text='Required')
    username = forms.CharField(label=_('Nombre de Usuario'))

    def __init__(self, *args, **kwargs):
        super(OrganizerUserSignupForm, self).__init__(*args, **kwargs)
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        # If one field gets autocompleted but not the other, our 'neither
        # password or both password' validation will be triggered.
        self.fields['password1'].widget.attrs['autocomplete'] = 'off'
        self.fields['password2'].widget.attrs['autocomplete'] = 'off'

        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        # TODO: ver layout para solo tener los campos requeridos.
        self.helper.layout = Layout(
            'username',
            'email',
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = super(OrganizerUserSignupForm, self).clean_password2()
        if bool(password1) ^ bool(password2):
            raise forms.ValidationError("Fill out both fields")
        return password2

    class Meta:
        model = User
        fields = ('username', 'email')


class EventUpdateForm(forms.ModelForm):
    start_date = forms.DateField(
        label=_('Fecha de inicio'),
        input_formats=settings.DATE_INPUT_FORMATS, help_text=_('Formato: DD/MM/AAAA'),
        widget=forms.widgets.DateInput(format=settings.DATE_INPUT_FORMATS[0]),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(EventUpdateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.fields['name'].disabled = True
        self.fields['commission'].disabled = True
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"

    class Meta:
        model = Event
        fields = ['name', 'commission', 'category', 'start_date', 'place']


class OrganizerUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(OrganizerUpdateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"

    class Meta:
        model = Organizer
        fields = ['first_name', 'last_name']


class SponsorCategoryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SponsorCategoryForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False

    class Meta:
        model = SponsorCategory
        fields = ['name', 'amount']


class BankAccountDataForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(BankAccountDataForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"

    class Meta:
        model = BankAccountData
        fields = [
            'organization_name', 'document_number', 'bank_entity',
            'account_type', 'account_number', 'cbu'
        ]

    def clean(self):
        super(BankAccountDataForm, self).clean()
        cbu_number = self.cleaned_data.get('cbu')
        validate_cbu(cbu_number=cbu_number, form=self)
        return self.cleaned_data


class SponsorForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SponsorForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-3"
        self.helper.field_class = "col-sm-9"

    class Meta:
        model = Sponsor
        fields = [
            'organization_name',
            'document_number',
            'vat_condition',
            'other_vat_condition_text',
            'address',
            'contact_info',
        ]
        widgets = {
            'contact_info': forms.Textarea(attrs={'rows': 4, 'cols': 40}),
        }


class SponsoringForm(forms.ModelForm):
    def __init__(self, event, *args, **kwargs):
        super(SponsoringForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"

        # Pre-filter sponsorcategory by event
        self.fields['sponsorcategory'].queryset = SponsorCategory.objects.filter(event=event)
        self.fields['sponsor'].queryset = Sponsor.objects.filter(enabled=True)

    class Meta:
        model = Sponsoring
        fields = [
            'sponsorcategory',
            'sponsor',
            'comments',
        ]
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 4, 'cols': 40}),
        }


class InvoiceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(InvoiceForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False

    class Meta:
        model = Invoice
        fields = [
            'amount',
            'observations',
            'document',
        ]


class InvoiceAffectForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(InvoiceAffectForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False

    class Meta:
        model = InvoiceAffect
        fields = [
            'category',
            'amount',
            'observations',
            'document',
        ]


class ProviderForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(ProviderForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        self.fields['bank_entity'].required = False
        self.fields['account_type'].required = False
        self.fields['account_number'].required = False
        self.fields['cbu'].required = False

    class Meta:
        model = Provider
        fields = [
            'organization_name',
            'document_number',
            'bank_entity',
            'account_type',
            'account_number',
            'cbu',
        ]

    def clean(self):
        super(ProviderForm, self).clean()
        cbu_number = self.cleaned_data.get('cbu')
        if len(cbu_number) > 0:
            validate_cbu(cbu_number=cbu_number, form=self)
        return self.cleaned_data


class ProviderExpenseForm(forms.ModelForm):
    invoice_date = forms.DateField(
        label=_('Fecha factura'),
        input_formats=settings.DATE_INPUT_FORMATS, help_text=_('Formato: DD/MM/AAAA'),
        widget=forms.widgets.DateInput(format=settings.DATE_INPUT_FORMATS[0]),
        required=True
    )

    def __init__(self, *args, **kwargs):
        super(ProviderExpenseForm, self).__init__(*args, **kwargs)
        # Pre-filter sponsorcategory by event
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"

    class Meta:
        model = ProviderExpense
        fields = [
            'provider',
            'amount',
            'invoice_type',
            'invoice_date',
            'invoice',
            'description',
        ]


class OrganizerRefundForm(forms.ModelForm):
    invoice_date = forms.DateField(
        label=_('Fecha factura'),
        input_formats=settings.DATE_INPUT_FORMATS, help_text=_('Formato: DD/MM/AAAA'),
        widget=forms.widgets.DateInput(format=settings.DATE_INPUT_FORMATS[0]),
        required=True
    )

    def __init__(self, event, *args, **kwargs):
        super(OrganizerRefundForm, self).__init__(*args, **kwargs)
        # Pre-filter sponsorcategory by event
        self.fields['organizer'].queryset = event.organizers.all()
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"

    class Meta:
        model = OrganizerRefund
        fields = [
            'organizer',
            'amount',
            'invoice_type',
            'invoice_date',
            'invoice',
            'description',
        ]


class PaymentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"

    class Meta:
        model = Payment
        fields = [
            'document',
        ]
