from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import ( 
    PasswordResetView, 
    PasswordResetConfirmView, 
    PasswordResetCompleteView,
    PasswordResetDoneView,
    LoginView,
    LogoutView
    )

from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import render, redirect

from django.urls import reverse_lazy
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _

import events
from events.helpers.tokens import account_activation_token
from events.forms import (
    OrganizerUserSignupForm, 
    SetPasswordForm, 
    AuthenticationForm, 
    PasswordResetForm
    )

# Class-based password reset views
# - PasswordResetView sends the mail
# - PasswordResetDoneView shows a success message for the above
# - PasswordResetConfirmView checks the link the user clicked and
#   prompts for a new password
# - PasswordResetCompleteView shows a success message for the above

class PasswordResetView(PasswordResetView):
    email_template_name = 'registration/custom_password_reset_email.html'
    extra_email_context = None
    form_class = PasswordResetForm
    from_email = None
    html_email_template_name = None
    subject_template_name = 'registration/custom_password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    template_name = 'registration/custom_password_reset_form.html'
    title = _('Reseteo de contraseña')
    token_generator = default_token_generator


class PasswordResetConfirmView(PasswordResetConfirmView):
    form_class = SetPasswordForm
    post_reset_login = False
    post_reset_login_backend = None
    success_url = reverse_lazy('password_reset_complete')
    template_name = 'registration/custom_password_reset_confirm.html'
    title = _('Ingrese nueva contraseña')
    token_generator = default_token_generator


class PasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/custom_password_reset_complete.html'
    title = _('Reseteo de contraseña completado')


class PasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/custom_password_reset_done.html'
    title = _('Cambio de contraseña enviado')


class LoginView(LoginView):
    form_class = AuthenticationForm
    template_name = 'registration/events_login.html'


class LogoutView(LogoutView):
    template_name = 'registration/custom_logged_out.html'


@login_required(login_url='/eventos/cuentas/login/')
def events_home(request):
    return render(request, 'events_home.html')

#TODO: change validation to verify if the user has add_organizer permision and not superuser
# permission_required('organizer.can_add')
@user_passes_test(lambda u: u.is_superuser, login_url='/eventos/cuentas/login/')
def organizer_signup(request):
    if request.method == 'POST':
        #Create user with random password and send custom reset password form
        form = OrganizerUserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(get_random_string())
            user.save()
            
            reset_form = PasswordResetForm({'email': user.email})
            assert reset_form.is_valid()
            reset_form.save(
                subject_template_name='registration/organizer_just_created_subject.txt',
                email_template_name='registration/organizer_set_password_email.html',
                request=request,
                use_https=request.is_secure(),
            )
            #TODO: create a organizer model, and redirect the user to the add organizers page
            return HttpResponse(_('Se le envio un mail al usuario organizador para que pueda ingresar sus credenciales de autenticación'))
    else:
        form = OrganizerUserSignupForm()
    return render(request, 'organizer_signup.html', {'form': form})


#TODO: delete just was to provee something
def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        # return redirect('home')
        return HttpResponse('Thank you for your email confirmation. Now you can login your account.')
    else:
        return HttpResponse('Activation link is invalid!')