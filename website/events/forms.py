from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Row

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