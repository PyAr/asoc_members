from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Row

from members.models import Person, Organization, Category, Member, Patron


class SignupPersonForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        label=_('Categoría'), queryset=Category.objects.order_by('-fee'),
        required=True, widget=forms.RadioSelect())

    birth_date = forms.DateField(
        label=_('Fecha de nacimiento'),
        input_formats=settings.DATE_INPUT_FORMATS, help_text=_('Formato: DD/MM/AAAA'))

    class Meta:
        model = Person
        fields = (
            'category',
            'first_name', 'last_name', 'document_number', 'email', 'nickname',
            'picture', 'nationality', 'marital_status', 'occupation', 'birth_date',
            'street_address', 'zip_code', 'city', 'province', 'country'
        )

    def __init__(self, *args, **kwargs):
        super(SignupPersonForm, self).__init__(*args, **kwargs)
        # make all fields required
        fields = [field for field in self.fields if field not in ('picture', 'nickname')]
        for field in fields:
            self.fields[field].required = True
        self.fields['category'].empty_label = None
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.form_class = 'form-horizontal'
        self.helper.layout = Layout(
            'category',
            Row(
                Div('first_name', css_class='col-xs-6'),
                Div('last_name', css_class='col-xs-6'),
            ),
            Row(
                Div('document_number', css_class='col-xs-6'),
                Div('email', css_class='col-xs-6'),
            ),
            Row(
                Div('nationality', css_class='col-xs-6'),
                Div('marital_status', css_class='col-xs-6'),
            ),
            Row(
                Div('occupation', css_class='col-xs-6'),
                Div('birth_date', css_class='col-xs-6'),
            ),
            Row(
                Div('street_address', css_class='col-xs-4'),
                Div('zip_code', css_class='col-xs-4'),
                Div('city', css_class='col-xs-4'),
            ),
            Row(
                Div('province', css_class='col-xs-6'),
                Div('country', css_class='col-xs-6'),
            ),
            Row(
                Div('nickname', css_class='col-xs-6'),
                Div('picture', css_class='col-xs-6'),
            ),
        )

    def save(self, commit=True):
        # We need remove category before save person.
        category = self.cleaned_data.pop('category', '')
        person = super(SignupPersonForm, self).save(commit=False)
        person.comments = (
            "Se cargó a través del sitio web. Categoria seleccionada: %s." % category.name)
        patron = Patron(
            name=f"{person.first_name} {person.last_name}",
            email=person.email, comments="Se cargó a través del sitio web")
        member = Member(registration_date=now(), category=category)
        if commit:
            patron.save()
            member.patron = patron
            member.save()
            person.membership = member
            person.save()
        return person

    def clean(self):
        super(SignupPersonForm, self).clean()

        # check that name, lastname and street cannot be all uppercase or lowercase
        name = self.cleaned_data.get("first_name", "")
        if name and (name == name.upper() or name == name.lower()):
            self.add_error('first_name', _('No escriba todo en minúsculas o todo en mayúsculas.'))

        last_name = self.cleaned_data.get("last_name", "")
        if last_name and (last_name == last_name.upper() or last_name == last_name.lower()):
            self.add_error('last_name', _('No escriba todo en minúsculas o todo en mayúsculas.'))

        street = self.cleaned_data.get("street_address", "")
        if street and (street == street.upper() or street == street.lower()):
            self.add_error(
                'street_address', _('No escriba todo en minúsculas o todo en mayúsculas.'))

        return self.cleaned_data

    def clean_nationality(self):
        data = self.cleaned_data.get('nationality', '').title()
        return data

    def clean_marital_status(self):
        data = self.cleaned_data.get('marital_status', '')
        return data.title()

    def clean_occupation(self):
        data = self.cleaned_data.get('occupation', '')
        return data.title()


class SignupOrganizationForm(forms.ModelForm):

    class Meta:
        model = Organization
        fields = ('name', 'contact_info', 'document_number', 'address', 'social_media')

    def __init__(self, *args, **kwargs):
        super(SignupOrganizationForm, self).__init__(*args, **kwargs)
        # make all fields required
        for field in self.fields:
            self.fields[field].required = True
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.form_class = 'form-horizontal'
        self.helper.layout = Layout(
            'name', 'contact_info',
            Row(
                Div('document_number', css_class='col-xs-6'),
                Div('address', css_class='col-xs-6'),
            ),
            'social_media'
        )

    def clean(self):
        super(SignupOrganizationForm, self).clean()

        # check that name, lastname and street cannot be all uppercase or lowercase
        name = self.cleaned_data.get("name", "")
        if name and (name == name.upper() or name == name.lower()):
            self.add_error('name', _('No escriba todo en minúsculas o todo en mayúsculas.'))

        street = self.cleaned_data.get("address", "")
        if street and (street == street.upper() or street == street.lower()):
            self.add_error('address', _('No escriba todo en minúsculas o todo en mayúsculas.'))

        return self.cleaned_data
