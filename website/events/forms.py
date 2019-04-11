from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm as AuthSetPasswordForm
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Row

from .constants import PASSWORD_VALIDATOR_HELP_TEXTS

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
        self.helper = FormHelper(self)
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
        #TODO: use crispy_forms
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = super(OrganizerUserSignupForm, self).clean_password2()
        if bool(password1) ^ bool(password2):
            raise forms.ValidationError("Fill out both fields")
        return password2

    class Meta:
        model = User
        fields = ('username', 'email')