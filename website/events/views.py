from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.sites.shortcuts import get_current_site

from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect

from django.shortcuts import get_object_or_404, redirect, render

from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.views import generic, View

from events.constants import (
    CANT_CHANGE_CLOSE_EVENT_MESSAGE,
    CAN_VIEW_EVENT_ORGANIZERS_CODENAME,
    DUPLICATED_SPONSOR_CATEGORY_MESSAGE,
    MUST_BE_ACCOUNT_OWNER_MESSAGE,
    MUST_BE_EVENT_ORGANIZAER_MESSAGE,
    MUST_BE_ORGANIZER_MESSAGE,
    ORGANIZER_MAIL_NOTOFICATION_MESSAGE
)
from events.forms import (
    BankAccountDataForm,
    EventUpdateForm,
    InvoiceForm,
    OrganizerUpdateForm,
    OrganizerUserSignupForm,
    SponsorForm,
    SponsorCategoryForm,
    SponsoringForm
)
from events.helpers.notifications import email_notifier
from events.helpers.views import seach_filterd_queryset
from events.helpers.permissions import is_event_organizer, ORGANIZER_GROUP_NAME
from events.models import (
    BankAccountData,
    Event,
    Invoice,
    Organizer,
    Sponsor,
    SponsorCategory,
    Sponsoring
)
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
            with transaction.atomic():
                # ensure that user, organizer and group association is atomic
                user = form.save(commit=False)
                user.set_password(get_random_string())
                user.save()
                group = Group.objects.get(name=ORGANIZER_GROUP_NAME)
                user.groups.add(group)
                # TODO: call a helper function to create de organizer with the correct group.
                Organizer.objects.create(user=user)

            reset_form = PasswordResetForm({'email': user.email})
            assert reset_form.is_valid()
            reset_form.save(
                subject_template_name='mails/organizer_just_created_subject.txt',
                email_template_name='mails/organizer_set_password_email.html',
                request=request,
                use_https=request.is_secure(),
                from_email=settings.EMAIL_FROM,
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
        # Must be event organizer.
        event = self.get_object()
        if ret and not is_event_organizer(self.request.user, event):
            self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
            return False
        return ret

    def handle_no_permission(self):
        if self.get_permission_denied_message() == MUST_BE_EVENT_ORGANIZAER_MESSAGE:
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


class BankOrganizerAccountDataUpdateView(PermissionRequiredMixin, generic.edit.UpdateView):
    model = BankAccountData
    form_class = BankAccountDataForm
    template_name = 'organizers/create_bank_account_data.html'
    permission_required = 'events.change_bankaccountdata'

    def has_permission(self):
        bank_account = self.get_object()
        ret = super(BankOrganizerAccountDataUpdateView, self).has_permission()
        try:
            organizer = self._get_organizer()
        except Organizer.DoesNotExist:
            self.permission_denied_message = MUST_BE_ORGANIZER_MESSAGE
            return False

        if ret and not bank_account.is_owner(organizer):
            self.permission_denied_message = MUST_BE_ACCOUNT_OWNER_MESSAGE
            return False

        return ret

    def handle_no_permission(self):
        if self.get_permission_denied_message() == MUST_BE_ACCOUNT_OWNER_MESSAGE:
            messages.add_message(self.request, messages.ERROR, MUST_BE_ACCOUNT_OWNER_MESSAGE)
            return redirect('organizer_detail', pk=self._get_organizer().pk)

        if self.get_permission_denied_message() == MUST_BE_ORGANIZER_MESSAGE:
            messages.add_message(self.request, messages.ERROR, MUST_BE_ORGANIZER_MESSAGE)
            return redirect('events_home')

        return super(BankOrganizerAccountDataUpdateView, self).handle_no_permission()

    def get_success_url(self):
        return self._get_organizer().get_absolute_url()

    def _get_organizer(self):
        return Organizer.objects.get(user=self.request.user)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BankOrganizerAccountDataUpdateView, self).get_context_data(**kwargs)
        context['organizer'] = self._get_organizer()
        return context


class BankOrganizerAccountDataCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = BankAccountData
    form_class = BankAccountDataForm
    template_name = 'organizers/create_bank_account_data.html'
    permission_required = 'events.add_bankaccountdata'

    def has_permission(self):
        ret = super(BankOrganizerAccountDataCreateView, self).has_permission()
        try:
            Organizer.objects.get(user=self.request.user)
        except Organizer.DoesNotExist:
            # TODO: add message requiring be an organizer user
            self.permission_denied_message = MUST_BE_ORGANIZER_MESSAGE
            return False
        return ret

    def handle_no_permission(self):
        if self.get_permission_denied_message() == MUST_BE_ORGANIZER_MESSAGE:
            messages.add_message(self.request, messages.ERROR, MUST_BE_ORGANIZER_MESSAGE)
            return redirect('events_home')

        return super(BankOrganizerAccountDataCreateView, self).handle_no_permission()

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BankOrganizerAccountDataCreateView, self).get_context_data(**kwargs)
        context['organizer'] = self._get_organizer()
        return context

    def form_valid(self, form):
        organizer = self._get_organizer()
        self.object = form.save()
        organizer.account_data = self.object
        organizer.save()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        ret = super(BankOrganizerAccountDataCreateView, self).form_invalid(form)
        return ret

    def get_success_url(self):
        return self._get_organizer().get_absolute_url()

    def _get_organizer(self):
        return get_object_or_404(Organizer, pk=self.kwargs['pk'])


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
        # Must be event organizer.
        if ret and not is_event_organizer(self.request.user, event):
            self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
            return False
        return ret

    def handle_no_permission(self):
        if self.get_permission_denied_message() == MUST_BE_EVENT_ORGANIZAER_MESSAGE:
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


class SponsorsListView(LoginRequiredMixin, generic.ListView):
    model = Sponsor
    context_object_name = 'sponsor_list'
    template_name = 'sponsors/sponsors_list.html'
    paginate_by = 5
    search_fields = {
        'organization_name': 'icontains',
        'document_number': 'icontains'
    }

    def get_queryset(self):
        queryset = super(SponsorsListView, self).get_queryset()
        # queryset = Sponsor.objects.all()
        search_value = self.request.GET.get('search', None)
        if search_value and search_value != '':
            queryset = seach_filterd_queryset(queryset, self.search_fields, search_value)
        return queryset


class SponsorCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = Sponsor
    form_class = SponsorForm
    template_name = 'sponsors/sponsor_form.html'
    permission_required = 'events.add_sponsor'

    def form_valid(self, form):
        ret = super(SponsorCreateView, self).form_valid(form)
        current_site = get_current_site(self.request)
        context = {
            'domain': current_site.domain,
            'protocol': 'https' if self.request.is_secure() else 'http'
        }
        sponsor = form.instance
        user = self.request.user
        email_notifier.send_new_sponsor_created(
            sponsor,
            user,
            context
        )
        return ret


class SponsorChangeView(PermissionRequiredMixin, generic.edit.UpdateView):
    model = Sponsor
    form_class = SponsorForm
    template_name = 'sponsors/sponsor_form.html'
    permission_required = 'events.change_sponsor'


class SponsorDetailView(LoginRequiredMixin, generic.DetailView):
    model = Sponsor
    template_name = 'sponsors/sponsor_detail.html'


class SponsorSetEnabled(PermissionRequiredMixin, View):
    permission_required = 'events.set_sponsors_enabled'

    def post(self, request, *args, **kwargs):
        sponsor = get_object_or_404(Sponsor, pk=kwargs['pk'])
        sponsor.enabled = True
        sponsor.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _('Patrocinador habilitado exitosamente ')
        )
        return redirect('sponsor_detail', pk=kwargs['pk'])


class SponsoringDetailView(PermissionRequiredMixin, generic.DetailView):
    model = Sponsoring
    template_name = 'events/sponsoring_detail.html'
    permission_required = 'events.change_event'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(SponsoringDetailView, self).get_context_data(**kwargs)
        event = self._get_event()
        context['event'] = event
        return context

    def has_permission(self):
        ret = super(SponsoringDetailView, self).has_permission()
        # Must be event organizer.
        event = self._get_event()
        if ret and not is_event_organizer(self.request.user, event):
            self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
            return False
        return ret

    def _get_event(self):
        return self.get_object().sponsorcategory.event

    def handle_no_permission(self):
        if self.get_permission_denied_message() == MUST_BE_EVENT_ORGANIZAER_MESSAGE:
            messages.add_message(self.request, messages.WARNING, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
            return redirect('event_list')
        else:
            return super(SponsoringDetailView, self).handle_no_permission()


class SponsoringCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = Sponsoring
    form_class = SponsoringForm
    template_name = 'events/sponsoring_form.html'
    permission_required = 'events.add_sponsoring'

    def get_form(self, form_class=None):
        event = self._get_event()
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(event, **self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(SponsoringCreateView, self).get_context_data(**kwargs)
        event = self._get_event()
        context['event'] = event
        return context

    def get(self, request, *args, **kwargs):
        event = self._get_event()
        exists_category = SponsorCategory.objects.filter(event=event).exists()
        exists_sponsors = Sponsor.objects.filter(enabled=True).exists()
        if not exists_category:
            messages.add_message(
                request,
                messages.WARNING,
                _('No se puede asociar patrocinios sin categorias de sponsor en el evento')
            )
        if not exists_sponsors:
            messages.add_message(
                request,
                messages.WARNING,
                _('No se puede asociar patrocinios sin sponsors habilitados')
            )

        if not exists_category or not exists_sponsors:
            return redirect('sponsoring_list', event_pk=event.pk)

        return super(SponsoringCreateView, self).get(request, *args, **kwargs)

    def _get_event(self):
        return get_object_or_404(Event, pk=self.kwargs['event_pk'])

    def has_permission(self):
        ret = super(SponsoringCreateView, self).has_permission()
        # Must be event organizer.
        event = self._get_event()
        if ret and not is_event_organizer(self.request.user, event):
            self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
            return False
        return ret

    def handle_no_permission(self):
        if self.get_permission_denied_message() == MUST_BE_EVENT_ORGANIZAER_MESSAGE:
            messages.add_message(self.request, messages.WARNING, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
            return redirect('event_list')
        else:
            return super(SponsoringCreateView, self).handle_no_permission()


class SponsoringListView(PermissionRequiredMixin, generic.ListView):
    model = Sponsoring
    context_object_name = 'sponsoring_list'
    template_name = 'events/sponsoring_list.html'
    permission_required = 'events.change_event'
    paginate_by = 10

    def get_queryset(self):
        queryset = super(SponsoringListView, self).get_queryset()
        event = self._get_event()
        return queryset.filter(sponsorcategory__event=event)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(SponsoringListView, self).get_context_data(**kwargs)
        event = self._get_event()
        context['event'] = event
        return context

    def _get_event(self):
        return get_object_or_404(Event, pk=self.kwargs['event_pk'])

    def has_permission(self):
        ret = super(SponsoringListView, self).has_permission()
        # Must be event organizer.
        event = self._get_event()
        if ret and not is_event_organizer(self.request.user, event):
            self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
            return False
        return ret


class InvoiceCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'events/sponsoring_invoice_form.html'
    permission_required = 'events.add_invoice'

    def form_valid(self, form):
        form.instance.sponsoring = self._get_sponsoring()
        return super(InvoiceCreateView, self).form_valid(form)

    def get_success_url(self):
        return self._get_sponsoring().get_absolute_url()

    def _get_sponsoring(self):
        return get_object_or_404(Sponsoring, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(InvoiceCreateView, self).get_context_data(**kwargs)
        context['sponsoring'] = self._get_sponsoring()
        context['event'] = self._get_sponsoring().sponsorcategory.event
        return context

    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().post(request, *args, **kwargs)
        except IntegrityError:
            messages.add_message(request, messages.ERROR, DUPLICATED_SPONSOR_CATEGORY_MESSAGE)
            return redirect('sponsoring_detail', pk=self._get_sponsoring().pk)

    def has_permission(self):
        event = self._get_sponsoring().sponsorcategory.event
        ret = super(InvoiceCreateView, self).has_permission()
        # Must be event organizer.
        if ret and not is_event_organizer(self.request.user, event):
            self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
            return False
        return ret

    def handle_no_permission(self):
        if self.get_permission_denied_message() == MUST_BE_EVENT_ORGANIZAER_MESSAGE:
            messages.add_message(self.request, messages.WARNING, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
            return redirect('sponsoring_detail', pk=self._get_sponsoring().pk)
        else:
            return super(InvoiceCreateView, self).handle_no_permission()


events_list = EventsListView.as_view()
event_detail = EventDetailView.as_view()
event_change = EventChangeView.as_view()
event_create_sponsor_category = SponsorCategoryCreateView.as_view()

organizers_list = OrganizersListView.as_view()
organizer_detail = OrganizerDetailView.as_view()
organizer_change = OrganizerChangeView.as_view()
organizer_create_bank_account_data = BankOrganizerAccountDataCreateView.as_view()
organizer_update_bank_account_data = BankOrganizerAccountDataUpdateView.as_view()

sponsors_list = SponsorsListView.as_view()
sponsor_detail = SponsorDetailView.as_view()
sponsor_change = SponsorChangeView.as_view()
sponsor_create = SponsorCreateView.as_view()
sponsor_set_enabled = SponsorSetEnabled.as_view()

sponsoring_list = SponsoringListView.as_view()
sponsoring_create = SponsoringCreateView.as_view()
sponsoring_detail = SponsoringDetailView.as_view()

sponsoring_invoice_create = InvoiceCreateView.as_view()
