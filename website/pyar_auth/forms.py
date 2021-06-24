from django import forms
from django.template.loader import render_to_string
from django.contrib.auth.forms import (
    AuthenticationForm as AuthAuthenticationForm,
    PasswordChangeForm as AuthPasswordChangeForm,
    PasswordResetForm as AuthPasswordResetForm,
    SetPasswordForm as AuthSetPasswordForm,
    UsernameField,
    )
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Button, Div, HTML
from crispy_forms.bootstrap import StrictButton

"""Helping constant for validate passwords, and custom atuthetication forms."""
ATTRIBUTE_SIMILARITY_HELP = _("La contraseña no puede ser similar a su otra información personal.")
COMMON_PASSWORD_HELP = _("La contraseña no puede ser comunmente usada.")
NUMERIC_PASSWORD_HELP = _("La constraseña no puede contener solo números.")
MINIMUM_LENGTH_HELP = _("La contraseña debe contener al menos 8 caracteres.")

PASSWORD_VALIDATOR_HELP_TEXTS = [
    ATTRIBUTE_SIMILARITY_HELP,
    COMMON_PASSWORD_HELP,
    NUMERIC_PASSWORD_HELP,
    MINIMUM_LENGTH_HELP,
    ]


class AuthenticationForm(AuthAuthenticationForm):
    """
    Base class for authenticating users.
    """
    username = UsernameField(label=_("Usuario"), widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(
        label=_("Contraseña"),
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
        self.helper.form_class = 'form-horizontal mt-50'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"



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
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"


class PasswordResetForm(AuthPasswordResetForm):
    email = forms.EmailField(label=_("Correo electrónico"), max_length=254)

    def __init__(self, *args, **kwargs):
        super(PasswordResetForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"


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
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        self.helper.layout = Layout(
            Div("old_password", "new_password1", "new_password2", css_class="mt-2"),
            StrictButton('<i class="fas fa-save"></i> Cambiar', type="submit", css_class="btn btn-success col-2 float-right mx-1"),
            HTML('<a class="btn btn-danger col-2 float-right mx-1" href="{{request.META.HTTP_REFERER}}"><i class="fas fa-undo"></i> Volver</a>'),
        )
