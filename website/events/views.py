from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from django.db import IntegrityError, transaction
from django.db.models import Q

from django.shortcuts import get_object_or_404, redirect, render

from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.views import generic, View

from events.constants import (
    CANT_CHANGE_CLOSE_EVENT_MESSAGE,
    CAN_VIEW_EVENT_ORGANIZERS_CODENAME,
    CAN_VIEW_ORGANIZERS_CODENAME,
    DUPLICATED_SPONSOR_CATEGORY_MESSAGE,
    MUST_BE_EVENT_ORGANIZAER_MESSAGE,
    ORGANIZER_MAIL_NOTOFICATION_MESSAGE
    )
from events.forms import (
    EventUpdateForm,
    OrganizerUpdateForm,
    OrganizerUserSignupForm,
    SponsorCategoryForm
    )
from events.helpers.views import seach_filterd_queryset
from events.models import Event, Organizer, SponsorCategory
from pyar_auth.forms import PasswordResetForm


@login_required()
def events_home(request):
    return render(request, 'events_home.html')


@permission_required('events.add_organizer')
def organizer_signup(request):
    if request.method == 'POST':
        # Create user with random password and send custom reset password form.
        form = OrganizerUserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(get_random_string())
            user.save()
            # TODO: call a helper function to create de organizer with the correct group.
            Organizer.objects.create(user=user)
            reset_form = PasswordResetForm({'email': user.email})
            assert reset_form.is_valid()
            reset_form.save(
                subject_template_name='mails/organizer_just_created_subject.txt',
                email_template_name='mails/organizer_set_password_email.html',
                request=request,
                use_https=request.is_secure(),
                from_email=settings.MAIL_FROM,
            )
            messages.add_message(
                request,
                messages.INFO,
                ORGANIZER_MAIL_NOTOFICATION_MESSAGE
            )
            return redirect('organizer_list')
    else:
        form = OrganizerUserSignupForm()
    return render(request, 'organizers/organizer_signup.html', {'form': form})


class EventsListView(LoginRequiredMixin, generic.ListView):
    model = Event
    context_object_name = 'event_list'
    template_name = 'events/event_list.html'
    paginate_by = 5
    search_fields = {
        'name': 'icontains',
        'place': 'icontains'
    }

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            queryset = Event.objects.all()
        else:
            organizers = Organizer.objects.filter(user=user)
            queryset = Event.objects.filter(organizers__in=organizers)

        search_value = self.request.GET.get('search', None)
        if search_value and search_value != '':
            queryset = seach_filterd_queryset(queryset, self.search_fields, search_value)
        return queryset


class EventDetailView(PermissionRequiredMixin, generic.DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    permission_required = 'events.change_event'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(EventDetailView, self).get_context_data(**kwargs)
        event = self.get_object()
        # Check that the user can see organizers and obtain them.
        user = self.request.user
        if user.has_perm('events.' + CAN_VIEW_EVENT_ORGANIZERS_CODENAME):
            organizers = event.organizers.all()
            context['organizers'] = organizers
        return context

    def has_permission(self):
        ret = super(EventDetailView, self).has_permission()
        if ret and not self.request.user.is_superuser:
            # Must be event organizer.
            event = self.get_object()
            try:
                organizer = Organizer.objects.get(user=self.request.user)
            except Organizer.DoesNotExist:
                organizer = None

            if organizer and (organizer in event.organizers.all()):
                return ret
            else:
                self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE

                return False

        return ret

    def handle_no_permission(self):
        if self.get_permission_denied_message()== MUST_BE_EVENT_ORGANIZAER_MESSAGE:
            messages.add_message(self.request, messages.WARNING, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
            return redirect('event_list')
        else:
            return super(EventDetailView, self).handle_no_permission() 


class EventChangeView(PermissionRequiredMixin, generic.edit.UpdateView):
    model = Event
    form_class = EventUpdateForm
    template_name = 'events/event_change.html'
    permission_required = 'events.change_event'

    def has_permission(self):
        event = self.get_object()
        ret = super(EventChangeView, self).has_permission()
        if ret and event.close:
            self.permission_denied_message = CANT_CHANGE_CLOSE_EVENT_MESSAGE
            return False

        return ret

    def handle_no_permission(self):
        if self.get_permission_denied_message() == CANT_CHANGE_CLOSE_EVENT_MESSAGE:
            messages.add_message(self.request, messages.ERROR, CANT_CHANGE_CLOSE_EVENT_MESSAGE)
            return redirect('event_detail', pk=self.get_object().pk)
        else:
            return super(EventChangeView, self).handle_no_permission()


class SponsorCategoryCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = SponsorCategory
    form_class = SponsorCategoryForm
    template_name = 'events/event_create_sponsor_category_modal.html'
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

    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().post(request, *args, **kwargs)
        except IntegrityError:
            messages.add_message(request, messages.ERROR, DUPLICATED_SPONSOR_CATEGORY_MESSAGE)
            return redirect('event_detail', pk=self._get_event().pk)

    def has_permission(self):
        event = self._get_event()
        ret = super(SponsorCategoryCreateView, self).has_permission()
        if ret and not self.request.user.is_superuser:
            try:
                organizer = Organizer.objects.get(user=self.request.user)
            except Organizer.DoesNotExist:
                organizer = None

            if organizer and (organizer in event.organizers.all()):
                return ret
            else:
                self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
                return False

        return ret

    def handle_no_permission(self):
        if self.get_permission_denied_message()== MUST_BE_EVENT_ORGANIZAER_MESSAGE:
            messages.add_message(self.request, messages.WARNING, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
            return redirect('event_detail', pk=self._get_event().pk)
        else:
            return super(SponsorCategoryCreateView, self).handle_no_permission() 


class OrganizersListView(PermissionRequiredMixin, generic.ListView):
    model = Organizer
    context_object_name = 'organizer_list'
    template_name = 'organizers/organizers_list.html'
    paginate_by = 5
    permission_required = 'events.view_organizers'
    search_fields = {
        'first_name': 'icontains',
        'last_name': 'icontains',
        'user__username': 'icontains'
    }

    def get_queryset(self):
        queryset = Organizer.objects.all()
        search_value = self.request.GET.get('search', None)
        if search_value and search_value != '':
            queryset = seach_filterd_queryset(queryset, self.search_fields, search_value)
        return queryset


class OrganizerDetailView(PermissionRequiredMixin, generic.DetailView):
    model = Organizer
    template_name = 'organizers/organizer_detail.html'
    permission_required = 'events.change_organizer'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(OrganizerDetailView, self).get_context_data(**kwargs)
        organizer = self.get_object()
        # Check that the user can see organizers and obtain them
        user = self.request.user
        context['is_request_user'] = organizer.user == user
        return context

    def has_permission(self):
        ret = super(OrganizerDetailView, self).has_permission()
        if not ret and self.request.user == self.get_object().user:
            # Can see own data.
            return True
        return ret


class OrganizerChangeView(PermissionRequiredMixin, generic.edit.UpdateView):
    model = Organizer
    form_class = OrganizerUpdateForm
    template_name = 'organizers/organizer_change.html'
    permission_required = ''

    def has_permission(self):
        return self.request.user == self.get_object().user


events_list = EventsListView.as_view()
event_detail = EventDetailView.as_view()
event_change = EventChangeView.as_view()
event_create_sponsor_category = SponsorCategoryCreateView.as_view()

organizers_list = OrganizersListView.as_view()
organizer_detail = OrganizerDetailView.as_view()
organizer_change = OrganizerChangeView.as_view()