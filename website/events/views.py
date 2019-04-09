from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User

from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string

from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

import events
from events.helpers.tokens import account_activation_token
from events.forms import OrganizerUserSignupForm


@user_passes_test(lambda u: u.is_superuser)
def organizer_signup(request):
    if request.method == 'POST':
        #Create user with random password and send custom reset password form
        form = OrganizerUserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(get_random_string())
            #user.is_active = False
            user.save()
            
            reset_form = PasswordResetForm({'email': user.email})
            assert reset_form.is_valid()
            reset_form.save(
                request=request,
                use_https=request.is_secure(),
            )

            return HttpResponse('An e-mail to reset password was sended to the new organizer user')
    else:
        form = OrganizerUserSignupForm()
    return render(request, 'organizer_signup.html', {'form': form})

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