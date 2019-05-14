from django import forms
from django.conf import settings
from django.contrib.auth.forms import (
    AuthenticationForm as AuthAuthenticationForm,
    PasswordChangeForm as AuthPasswordChangeForm,
    PasswordResetForm as AuthPasswordResetForm,
    SetPasswordForm as AuthSetPasswordForm,
    UserCreationForm, 
    UsernameField,
    )
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Row

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from events.constants import PASSWORD_VALIDATOR_HELP_TEXTS
from events.models import Event, Organizer, SponsorCategory

class AuthenticationForm(AuthAuthenticationForm):
    """
    Base class for authenticating users.
    """
    username = UsernameField(label=_("Usuario"), widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput,
    )

    error_messages = {
        'invalid_login': _(
            "Por favor ingrese un correcto nombre de usuario y password. Note que ambos "
            "campos pueden ser sensibles a mayúsculas."
        ),
        'inactive': _("Esta cuenta no se encuentra activa."),
    }
    
    def __init__(self, *args, **kwargs):
        super(AuthenticationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False


class SetPasswordForm(AuthSetPasswordForm):
    error_messages = {
        'password_mismatch': _("Las contraseñas no coinciden."),
    }
    new_password1 = forms.CharField(
        label=_("Nueva contraseña"),
        widget=forms.PasswordInput,
        help_text=render_to_string('registration/password_validations.html',{
            'helpers': PASSWORD_VALIDATOR_HELP_TEXTS
        }),
    )
    new_password2 = forms.CharField(
        label=_("Confirmación de nueva contraseña"),
        widget=forms.PasswordInput,
        help_text=_('Ingrese la mimsa contraseña que antes para verificar')
        )

    def __init__(self, *args, **kwargs):
        super(SetPasswordForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
    

class PasswordResetForm(AuthPasswordResetForm):
    email = forms.EmailField(label=_("Correo electrónico"), max_length=254)

    def __init__(self, *args, **kwargs):
        super(PasswordResetForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False


class PasswordChangeForm(AuthPasswordChangeForm):
    error_messages = dict(SetPasswordForm.error_messages, **{
        'password_incorrect': _("Su antiguo password fue introducido incorrectamente. "
                                "Por favor ingreselo otra vez."),
    })

    old_password = forms.CharField(
        label=_("Antigua contraseña"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autofocus': True}),
    )
    new_password1 = forms.CharField(
        label=_("Nueva contraseña"),
        widget=forms.PasswordInput,
        help_text=render_to_string('registration/password_validations.html',{
            'helpers': PASSWORD_VALIDATOR_HELP_TEXTS
        }),
    )
    new_password2 = forms.CharField(
        label=_("Confirmación de nueva contraseña"),
        widget=forms.PasswordInput,
        help_text=_('Ingrese la mimsa contraseña que antes para verificar')
    )

    def __init__(self, *args, **kwargs):
        super(PasswordChangeForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False


class OrganizerUserSignupForm(UserCreationForm):
    email = forms.EmailField(label=_('Correo Electrónico'), max_length=200, help_text='Required')
    username = forms.CharField(label = _('Nombre de Usuario'))

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
        #TODO: ver layout para solo tener los campos requeridos 
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
    start_date = forms.DateField(label=_('Fecha de inicio'),
        input_formats=settings.DATE_INPUT_FORMATS, help_text=_('Formato: DD/MM/AAAA'), 
        widget=forms.widgets.DateInput(format=settings.DATE_INPUT_FORMATS[0]), required=False)

    def __init__(self, *args, **kwargs):
        super(EventUpdateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
    
    def clean_name(self):
        # when field is cleaned, we always return the existing model field.
        return self.instance.name
    
    def clean_commission(self):
        # when field is cleaned, we always return the existing model field.
        return self.instance.commission

    class Meta:
        model = Event
        fields = ['name', 'commission', 'category', 'start_date', 'place']
        widgets = {
            'name': forms.TextInput(attrs={'readonly': True}),
            'commission': forms.TextInput(attrs={'readonly': True}),
        }


class OrganizerUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(OrganizerUpdateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False

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
