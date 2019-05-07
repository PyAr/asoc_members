from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import user_passes_test, login_required, permission_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
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
from django.shortcuts import get_object_or_404, redirect, render  

from django.urls import reverse_lazy
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from django.views import generic, View

from events.constants import (
    CAN_VIEW_ORGANIZERS_CODENAME,
    CAN_ASSOCIATE_ORGANIZER_CODENAME,
    LOGIN_URL,
    MUST_BE_EVENT_ORGANIZAER_MESSAGE
    )
from events.forms import (
    AuthenticationForm,
    EventUpdateForm,
    OrganizerUserSignupForm,
    PasswordResetForm,
    SetPasswordForm,
    SponsorCategoryForm
    )
from events.helpers.tokens import account_activation_token
from events.models import Event, Organizer, SponsorCategory

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
    subject_template_name = 'mails/custom_password_reset_subject.txt'
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
@permission_required('events.add_organizer', login_url='/eventos/cuentas/login/')
def organizer_signup(request):
    if request.method == 'POST':
        #Create user with random password and send custom reset password form
        form = OrganizerUserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(get_random_string())
            user.save()
            #TODO: call a helper function to create de organizer with the correct group
            Organizer.objects.create(user=user)
            reset_form = PasswordResetForm({'email': user.email})
            assert reset_form.is_valid()
            reset_form.save(
                subject_template_name='mails/organizer_just_created_subject.txt',
                email_template_name='mails/organizer_set_password_email.html',
                request=request,
                use_https=request.is_secure(),
            )
            #TODO: Redirect the user to the add organizers page, or add message of organizer created
            return HttpResponse(_('Se le envio un mail al usuario organizador para que pueda ingresar sus credenciales de autenticación'))
    else:
        form = OrganizerUserSignupForm()
    return render(request, 'organizer_signup.html', {'form': form})


class EventsListView(LoginRequiredMixin, generic.ListView):
    login_url = LOGIN_URL
    model = Event
    context_object_name = 'event_list'
    template_name = 'event_list.html'
    paginate_by = 5

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            queryset = Event.objects.all()
        else:
            organizers = Organizer.objects.filter(user=user)
            queryset = Event.objects.filter(organizers__in=organizers)
        
        return queryset


class EventDetailView(PermissionRequiredMixin, generic.DetailView):
    login_url = LOGIN_URL
    model = Event
    template_name = 'event_detail.html'
    permission_required = 'events.change_event'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(EventDetailView, self).get_context_data(**kwargs)
        event = self.get_object()
        # Check that the user can see organizers and obtain them
        user = self.request.user
        if user.has_perm('events.' + CAN_VIEW_ORGANIZERS_CODENAME):
            organizers = event.organizers.all()
            context['organizers'] = organizers
        return context
    
    def has_permission(self):
        ret = super(EventDetailView, self).has_permission()
        if ret and not self.request.user.is_superuser:
            #tiene que se organizador del evento
            event = self.get_object()
            try:
                organizer = Organizer.objects.get(user=self.request.user)
            except Organizer.DoesNotExist:
                organizer = None
            
            if organizer and (organizer in event.organizers.all()):
                return ret
            else:
                self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
                messages.add_message(self.request, messages.WARNING, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
                return False
            
        return ret

    def handle_no_permission(self):
        if self.get_permission_denied_message()== MUST_BE_EVENT_ORGANIZAER_MESSAGE:
            return redirect('event_list')
        else:
            return super(EventDetailView, self).handle_no_permission() 
            

class EventChangeView(PermissionRequiredMixin, generic.edit.UpdateView):
    login_url = LOGIN_URL
    model = Event
    form_class = EventUpdateForm
    template_name = 'event_change.html'
    permission_required = 'events.change_event'


class SponsorCategoryCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    login_url = LOGIN_URL
    model = SponsorCategory
    form_class = SponsorCategoryForm
    template_name = 'event_create_sponsor_category_modal.html'
    permission_required = 'events.add_sponsorcategory'
    
    def form_valid(self, form):
        form.instance.event = self._get_event()
        return super(SponsorCategoryCreateView, self).form_valid(form)

    def get_success_url(self):
        return self._get_event().get_absolute_url()

    def _get_event(self):
        return get_object_or_404(Event, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(SponsorCategoryCreateView, self).get_context_data(**kwargs)
        context['event'] = self._get_event()
        return context
        


events_list = EventsListView.as_view()
event_detail = EventDetailView.as_view()
event_change = EventChangeView.as_view()
event_create_sponsor_category = SponsorCategoryCreateView.as_view()