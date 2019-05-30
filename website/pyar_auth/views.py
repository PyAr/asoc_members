from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    PasswordResetDoneView,
    LoginView,
    LogoutView
    )
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from .forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm
    )
from django.views import generic

# Class-based password reset views
# - PasswordResetView sends the mail
# - PasswordResetDoneView shows a success message for the above
# - PasswordResetConfirmView checks the link the user clicked and
#   prompts for a new password
# - PasswordResetCompleteView shows a success message for the above


class PasswordResetView(PasswordResetView):
    extra_email_context = None
    form_class = PasswordResetForm
    from_email = settings.EMAIL_FROM
    html_email_template_name = None
    success_url = reverse_lazy('password_reset_done')
    title = _('Reseteo de contraseña')
    token_generator = default_token_generator


class PasswordResetConfirmView(PasswordResetConfirmView):
    form_class = SetPasswordForm
    post_reset_login = False
    post_reset_login_backend = None
    success_url = reverse_lazy('password_reset_complete')
    title = _('Ingrese nueva contraseña')
    token_generator = default_token_generator


class LoginView(LoginView):
    form_class = AuthenticationForm


def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, _('Su password fue exitosamente actualizado'))
            return redirect('change_password')
        else:
            messages.error(request, _('Por favor corriga los errores marcados'))
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'registration/change_password.html', {
        'form': form
    })


class ProfileView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'profile.html'
