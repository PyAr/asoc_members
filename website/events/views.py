from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.sites.shortcuts import get_current_site

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect, JsonResponse

from django.shortcuts import get_object_or_404, redirect, render

from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.views import generic, View

from events.constants import (
    CANT_CHANGE_CLOSE_EVENT_MESSAGE,
    CAN_VIEW_EVENT_ORGANIZERS_CODENAME,
    DEFAULT_PAGINATION,
    DUPLICATED_SPONSOR_CATEGORY_MESSAGE,
    INVOICE_APPOVED_MESSAGE,
    INVOICE_SET_COMPLETE_PAYMENT_MESSAGE,
    INVOICE_SET_PARTIAL_PAYMENT_MESSAGE,
    MUST_BE_ACCOUNT_OWNER_MESSAGE,
    MUST_BE_APPROVED_INVOICE_MESSAGE,
    MUST_BE_EVENT_ORGANIZAER_MESSAGE,
    MUST_BE_ORGANIZER_MESSAGE,
    MUST_EXISTS_SPONSOR_CATEGORY_MESSAGE,
    MUST_EXISTS_SPONSOR_MESSAGE,
    MUST_EXISTS_PROVIDERS_MESSAGE,
    ORGANIZER_MAIL_NOTOFICATION_MESSAGE,
    SPONSORING_SUCCESSFULLY_CLOSE_MESSAGE,
    CANT_CHANGE_PROVIDER_EXPENSE_WITH_PAYMENT,
    EXPENSE_MODIFIED,
)
from events.forms import (
    BankAccountDataForm,
    EventUpdateForm,
    InvoiceForm,
    InvoiceAffectForm,
    OrganizerRefundForm,
    OrganizerUpdateForm,
    OrganizerUserSignupForm,
    PaymentForm,
    ProviderForm,
    ProviderExpenseForm,
    SponsorForm,
    SponsorCategoryForm,
    SponsoringForm
)
from events.helpers.notifications import email_notifier
from events.helpers.task import calculate_organizer_task, calculate_super_user_task
from events.helpers.views import search_filtered_queryset
from events.helpers.permissions import is_event_organizer, ORGANIZER_GROUP_NAME, is_organizer_user
from events.models import (
    BankAccountData,
    Event,
    Expense,
    Invoice,
    InvoiceAffect,
    Organizer,
    OrganizerRefund,
    Payment,
    Provider,
    ProviderExpense,
    Sponsor,
    SponsorCategory,
    Sponsoring
)
from events.helpers.sponsoring_pending import (
    calculate_sponsoring_pending,
)
from pyar_auth.forms import PasswordResetForm


@login_required()
def events_home(request):
    user = request.user
    tasks = []
    sponsoring_pending = []
    if Organizer.objects.filter(user=user).exists():
        tasks = calculate_organizer_task(user)
        sponsoring_pending = calculate_sponsoring_pending(user)
    else:
        if user.is_superuser:
            tasks = calculate_super_user_task()
            sponsoring_pending = calculate_sponsoring_pending()

    return render(request, 'events_home.html', {
        'tasks': tasks,
        'sponsoring_pending': sponsoring_pending,
    })


@permission_required('events.add_organizer')
def organizer_signup(request):
    if request.method == 'POST':
        # Create user with random password and send custom reset password form.
        form = OrganizerUserSignupForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Ensure that user, organizer, and group association is atomic.
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
    paginate_by = DEFAULT_PAGINATION
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
            queryset = search_filtered_queryset(queryset, self.search_fields, search_value)
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
    paginate_by = DEFAULT_PAGINATION
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
            queryset = search_filtered_queryset(queryset, self.search_fields, search_value)
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
    paginate_by = DEFAULT_PAGINATION
    search_fields = {
        'organization_name': 'icontains',
        'document_number': 'icontains'
    }

    def get_queryset(self):
        queryset = super(SponsorsListView, self).get_queryset()
        # queryset = Sponsor.objects.all()
        search_value = self.request.GET.get('search', None)
        if search_value and search_value != '':
            queryset = search_filtered_queryset(queryset, self.search_fields, search_value)
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
        current_site = get_current_site(self.request)
        context = {
            'domain': current_site.domain,
            'protocol': 'https' if self.request.is_secure() else 'http'
        }
        email_notifier.send_sponsor_enabled(
            sponsor,
            context
        )
        return redirect('sponsor_detail', pk=kwargs['pk'])


class SponsoringDetailView(PermissionRequiredMixin, generic.DetailView):
    model = Sponsoring
    template_name = 'events/sponsorings/sponsoring_detail.html'
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
    template_name = 'events/sponsorings/sponsoring_form.html'
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

    def form_valid(self, form):
        ret = super(SponsoringCreateView, self).form_valid(form)
        current_site = get_current_site(self.request)
        context = {
            'domain': current_site.domain,
            'protocol': 'https' if self.request.is_secure() else 'http'
        }
        sponsoring = form.instance
        email_notifier.send_new_sponsoring_created(
            sponsoring,
            self.request.user,
            context
        )
        return ret

    def get(self, request, *args, **kwargs):
        event = self._get_event()
        exists_category = SponsorCategory.objects.filter(event=event).exists()
        exists_sponsors = Sponsor.objects.filter(enabled=True).exists()
        if not exists_category:
            messages.add_message(
                request,
                messages.WARNING,
                MUST_EXISTS_SPONSOR_CATEGORY_MESSAGE
            )
        if not exists_sponsors:
            messages.add_message(
                request,
                messages.WARNING,
                MUST_EXISTS_SPONSOR_MESSAGE
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
    template_name = 'events/sponsorings/sponsoring_list.html'
    permission_required = 'events.change_event'
    paginate_by = DEFAULT_PAGINATION

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

    def handle_no_permission(self):
        if self.get_permission_denied_message() == MUST_BE_EVENT_ORGANIZAER_MESSAGE:
            messages.add_message(self.request, messages.WARNING, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
            return redirect('event_list')
        else:
            return super(SponsoringListView, self).handle_no_permission()


class SponsoringSetClose(PermissionRequiredMixin, View):
    permission_required = 'events.close_sponsoring'

    def post(self, request, *args, **kwargs):
        sponsoring = get_object_or_404(Sponsoring, pk=kwargs['pk'])
        sponsoring.close = True
        sponsoring.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            SPONSORING_SUCCESSFULLY_CLOSE_MESSAGE
        )
        return redirect('sponsoring_detail', pk=kwargs['pk'])


class InvoiceCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'events/sponsorings/sponsoring_invoice_form.html'
    permission_required = 'events.add_invoice'

    def get_initial(self, *args, **kwargs):
        sponsoring = self._get_sponsoring()
        initial = super(InvoiceCreateView, self).get_initial(**kwargs)
        initial['amount'] = sponsoring.sponsorcategory.amount
        return initial

    def form_valid(self, form):
        form.instance.sponsoring = self._get_sponsoring()
        ret = super(InvoiceCreateView, self).form_valid(form)
        current_site = get_current_site(self.request)
        context = {
            'domain': current_site.domain,
            'protocol': 'https' if self.request.is_secure() else 'http'
        }
        invoice = form.instance
        email_notifier.send_new_invoice_created(
            invoice,
            context
        )
        return ret

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.is_ajax():
            return JsonResponse(form.errors, status=400)
        else:
            return response

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
            return redirect('event_list')
        else:
            return super(InvoiceCreateView, self).handle_no_permission()


class InvoiceSetAproved(PermissionRequiredMixin, View):
    permission_required = 'events.set_invoice_approved'

    def post(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=kwargs['pk'])
        invoice.invoice_ok = True
        invoice.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            INVOICE_APPOVED_MESSAGE
        )
        return redirect('sponsoring_detail', pk=invoice.sponsoring.pk)


class InvoiceSetCompletePayment(PermissionRequiredMixin, View):
    permission_required = 'events.set_invoice_complete_payment'

    def post(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=kwargs['pk'])
        invoice.complete_payment = True
        invoice.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            INVOICE_SET_COMPLETE_PAYMENT_MESSAGE
        )
        return redirect('sponsoring_detail', pk=invoice.sponsoring.pk)


class InvoiceSetPartialPayment(PermissionRequiredMixin, View):
    permission_required = 'events.set_invoice_partial_payment'

    def post(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=kwargs['pk'])
        invoice.partial_payment = True
        invoice.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            INVOICE_SET_PARTIAL_PAYMENT_MESSAGE
        )
        return redirect('sponsoring_detail', pk=invoice.sponsoring.pk)


class InvoiceAffectCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = InvoiceAffect
    form_class = InvoiceAffectForm
    template_name = 'events/sponsorings/sponsoring_invoice_affect_form.html'
    permission_required = 'events.add_invoiceaffect'

    def form_valid(self, form):
        form.instance.invoice = self._get_invoice()
        ret = super(InvoiceAffectCreateView, self).form_valid(form)
        current_site = get_current_site(self.request)
        context = {
            'domain': current_site.domain,
            'protocol': 'https' if self.request.is_secure() else 'http'
        }
        invoice_affect = form.instance
        user = self.request.user
        email_notifier.send_new_invoice_affect_created(
            invoice_affect,
            user,
            context
        )
        return ret

    def _get_invoice(self):
        return get_object_or_404(Invoice, pk=self.kwargs['pk'])

    def _get_sponsoring(self):
        return self._get_invoice().sponsoring

    def get_success_url(self):
        return self._get_sponsoring().get_absolute_url()

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(InvoiceAffectCreateView, self).get_context_data(**kwargs)
        context['invoice'] = self._get_invoice()
        return context

    def has_permission(self):
        event = self._get_sponsoring().sponsorcategory.event
        ret = super(InvoiceAffectCreateView, self).has_permission()
        # Must be event organizer.
        if ret and not is_event_organizer(self.request.user, event):
            self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
            return False
        if ret and not self._get_invoice().invoice_ok:
            self.permission_denied_message = MUST_BE_APPROVED_INVOICE_MESSAGE
            return False

        return ret

    def handle_no_permission(self):
        message = self.get_permission_denied_message()
        if message in [MUST_BE_EVENT_ORGANIZAER_MESSAGE, MUST_BE_APPROVED_INVOICE_MESSAGE]:
            messages.add_message(self.request, messages.WARNING, message)
            return redirect('sponsoring_detail', pk=self._get_sponsoring().pk)
        else:
            return super(InvoiceAffectCreateView, self).handle_no_permission()


class ProvidersListView(LoginRequiredMixin, generic.ListView):
    model = Provider
    context_object_name = 'provider_list'
    template_name = 'providers/providers_list.html'
    paginate_by = DEFAULT_PAGINATION
    search_fields = {
        'organization_name': 'icontains',
        'document_number': 'icontains'
    }

    def get_queryset(self):
        queryset = super(ProvidersListView, self).get_queryset()
        # queryset = Sponsor.objects.all()
        search_value = self.request.GET.get('search', None)
        if search_value and search_value != '':
            queryset = search_filtered_queryset(queryset, self.search_fields, search_value)
        return queryset


class ProviderCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = Provider
    form_class = ProviderForm
    template_name = 'providers/provider_form.html'
    permission_required = 'events.add_provider'


class ProviderChangeView(PermissionRequiredMixin, generic.edit.UpdateView):
    model = Provider
    form_class = ProviderForm
    template_name = 'providers/provider_form.html'
    permission_required = 'events.change_provider'


class ProviderDetailView(LoginRequiredMixin, generic.DetailView):
    model = Provider
    template_name = 'providers/provider_detail.html'


class ExpensesListView(PermissionRequiredMixin, generic.ListView):
    model = Expense
    context_object_name = 'expenses_list'
    template_name = 'events/expenses/expenses_list.html'
    permission_required = 'events.view_expenses'
    paginate_by = DEFAULT_PAGINATION
    search_fields = {
        'description': 'icontains',
        'providerexpense__provider__organization_name': 'icontains',
        'organizerrefund__organizer__user__username': 'icontains',
    }

    def get_queryset(self):
        queryset = super(ExpensesListView, self).get_queryset()
        event = self._get_event()
        queryset = queryset.filter(event=event)

        search_value = self.request.GET.get('search', None)
        if search_value and search_value != '':
            queryset = search_filtered_queryset(queryset, self.search_fields, search_value)
        return queryset

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(ExpensesListView, self).get_context_data(**kwargs)
        event = self._get_event()
        context['event'] = event
        if is_organizer_user(self.request.user):
            context['organizer'] = Organizer.objects.get(user=self.request.user)
        return context

    def _get_event(self):
        return get_object_or_404(Event, pk=self.kwargs['event_pk'])

    def has_permission(self):
        ret = super(ExpensesListView, self).has_permission()
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
            return super(ExpensesListView, self).handle_no_permission()


class ProviderExpenseCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = ProviderExpense
    form_class = ProviderExpenseForm
    template_name = 'events/expenses/provider_expense_form.html'
    permission_required = 'events.add_providerexpense'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(ProviderExpenseCreateView, self).get_context_data(**kwargs)
        event = self._get_event()
        context['event'] = event
        return context

    def form_valid(self, form):
        form.instance.event = self._get_event()
        ret = super(ProviderExpenseCreateView, self).form_valid(form)
        current_site = get_current_site(self.request)
        context = {
            'domain': current_site.domain,
            'protocol': 'https' if self.request.is_secure() else 'http'
        }
        user = self.request.user
        expense = form.instance
        email_notifier.send_new_expense_created(
            expense,
            user,
            context
        )
        return ret

    def get(self, request, *args, **kwargs):
        event = self._get_event()
        exists_provider = (Provider.objects.count() > 0)

        if not exists_provider:
            messages.add_message(
                request,
                messages.WARNING,
                MUST_EXISTS_PROVIDERS_MESSAGE
            )
            return redirect('expenses_list', event_pk=event.pk)
        return super(ProviderExpenseCreateView, self).get(request, *args, **kwargs)

    def _get_event(self):
        return get_object_or_404(Event, pk=self.kwargs['event_pk'])

    def has_permission(self):
        ret = super(ProviderExpenseCreateView, self).has_permission()
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
            return super(ProviderExpenseCreateView, self).handle_no_permission()


class OrganizerRefundCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = OrganizerRefund
    form_class = OrganizerRefundForm
    template_name = 'events/expenses/organizer_refund_form.html'
    permission_required = 'events.add_organizerrefund'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(OrganizerRefundCreateView, self).get_context_data(**kwargs)
        event = self._get_event()
        context['event'] = event
        return context

    def get_form(self, form_class=None):
        event = self._get_event()
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(event, **self.get_form_kwargs())

    def get_initial(self, *args, **kwargs):
        initial = super(OrganizerRefundCreateView, self).get_initial(**kwargs)
        if Organizer.objects.filter(user=self.request.user).exists():
            initial['organizer'] = Organizer.objects.get(user=self.request.user)
        return initial

    def form_valid(self, form):
        form.instance.event = self._get_event()
        ret = super(OrganizerRefundCreateView, self).form_valid(form)
        current_site = get_current_site(self.request)
        context = {
            'domain': current_site.domain,
            'protocol': 'https' if self.request.is_secure() else 'http'
        }
        user = self.request.user
        expense = form.instance
        email_notifier.send_new_expense_created(
            expense,
            user,
            context
        )
        return ret

    def get(self, request, *args, **kwargs):
        event = self._get_event()
        exists_provider = (Provider.objects.count() > 0)

        if not exists_provider:
            messages.add_message(
                request,
                messages.WARNING,
                MUST_EXISTS_SPONSOR_CATEGORY_MESSAGE
            )
            return redirect('expenses_list', event_pk=event.pk)
        return super(OrganizerRefundCreateView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        url = reverse('expenses_list', kwargs={'event_pk': self._get_event().pk})
        return url

    def _get_event(self):
        return get_object_or_404(Event, pk=self.kwargs['event_pk'])

    def has_permission(self):
        ret = super(OrganizerRefundCreateView, self).has_permission()
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
            return super(OrganizerRefundCreateView, self).handle_no_permission()


class ProviderExpenseDetailView(PermissionRequiredMixin, generic.DetailView):
    model = ProviderExpense
    template_name = 'events/expenses/provider_expense_detail.html'
    permission_required = 'events.view_expenses'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(ProviderExpenseDetailView, self).get_context_data(**kwargs)
        event = self._get_event()
        context['event'] = event
        return context

    def has_permission(self):
        ret = super(ProviderExpenseDetailView, self).has_permission()
        # Must be event organizer.
        event = self._get_event()
        if ret and not is_event_organizer(self.request.user, event):
            self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
            return False
        return ret

    def _get_event(self):
        return self.get_object().event

    def handle_no_permission(self):
        if self.get_permission_denied_message() == MUST_BE_EVENT_ORGANIZAER_MESSAGE:
            messages.add_message(self.request, messages.WARNING, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
            return redirect('event_list')
        else:
            return super(ProviderExpenseDetailView, self).handle_no_permission()


class ProviderExpensePaymentCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'events/expenses/provider_expense_payment_form.html'
    permission_required = 'events.add_payment'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(ProviderExpensePaymentCreateView, self).get_context_data(**kwargs)
        expense = self._get_expense()
        context['expense'] = expense
        return context

    def form_valid(self, form):
        with transaction.atomic():
            ret = super(ProviderExpensePaymentCreateView, self).form_valid(form)
            expense = self._get_expense()
            expense.payment = form.instance
            expense.save()
            current_site = get_current_site(self.request)
            context = {
                'domain': current_site.domain,
                'protocol': 'https' if self.request.is_secure() else 'http'
            }
            email_notifier.send_new_provider_payment_created(
                expense,
                context
            )
            return ret

    def get_success_url(self):
        return self._get_expense().get_absolute_url()

    def _get_expense(self):
        return get_object_or_404(ProviderExpense, pk=self.kwargs['pk'])


class OrganizerRefundDetailView(PermissionRequiredMixin, generic.DetailView):
    model = OrganizerRefund
    template_name = 'events/expenses/organizer_refund_detail.html'
    permission_required = 'events.view_expenses'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(OrganizerRefundDetailView, self).get_context_data(**kwargs)
        event = self._get_event()
        context['event'] = event
        return context

    def has_permission(self):
        ret = super(OrganizerRefundDetailView, self).has_permission()
        # Must be event organizer.
        event = self._get_event()
        if ret and not is_event_organizer(self.request.user, event):
            self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
            return False
        return ret

    def _get_event(self):
        return self.get_object().event

    def handle_no_permission(self):
        if self.get_permission_denied_message() == MUST_BE_EVENT_ORGANIZAER_MESSAGE:
            messages.add_message(self.request, messages.WARNING, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
            return redirect('event_list')
        else:
            return super(OrganizerRefundDetailView, self).handle_no_permission()


class OrganizerRefundPaymentCreateView(PermissionRequiredMixin, generic.edit.CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'events/expenses/organizer_refunds_payment_form.html'
    permission_required = 'events.add_payment'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(OrganizerRefundPaymentCreateView, self).get_context_data(**kwargs)
        go_to = self.request.GET.get('next', None)
        organizer = self._get_organizer()
        context['organizer'] = organizer
        refunds = OrganizerRefund.objects.filter(
            organizer=organizer,
            payment__isnull=True,
            cancelled_date__isnull=True,
        ).all()
        context['refunds'] = refunds
        context['go_to'] = go_to
        return context

    def form_valid(self, form):
        if 'refunds' in self.request.POST:
            refunds = []
            refunds_ids = self.request.POST.getlist('refunds')
            for refund_id in refunds_ids:
                try:
                    refund = OrganizerRefund.objects.get(pk=refund_id)
                except OrganizerRefund.DoesNotExist:
                    form.add_error(
                        None,
                        ValidationError(_("Uno de los reintegros pasados no existe")))
                    return super(OrganizerRefundPaymentCreateView, self).form_invalid(form)
                if refund.payment:
                    message = _(
                        f"El reintegro {refund.pk} con monto "
                        f"{refund.amount} ya tiene pago adjunto")
                    form.add_error(
                        None,
                        ValidationError(message))
                    return super(OrganizerRefundPaymentCreateView, self).form_invalid(form)
                refunds.append(refund)
        else:
            form.add_error(
                None,
                ValidationError(_("No se puede adjuntar sin seleccionar reintegros")))
            return super(OrganizerRefundPaymentCreateView, self).form_invalid(form)

        with transaction.atomic():
            ret = super(OrganizerRefundPaymentCreateView, self).form_valid(form)
            for refund in refunds:
                refund.payment = form.instance
                refund.save()
            current_site = get_current_site(self.request)
            context = {
                'domain': current_site.domain,
                'protocol': 'https' if self.request.is_secure() else 'http'
            }
            email_notifier.send_new_organizer_payment_created(
                refunds,
                self._get_organizer(),
                context
            )
            return ret

    def get_success_url(self):
        go_to = self.request.GET.get('next', None)
        if go_to:
            return go_to
        return self._get_organizer().get_absolute_url()

    def _get_organizer(self):
        return get_object_or_404(Organizer, pk=self.kwargs['pk'])


class ProviderExpenseUpdateView(PermissionRequiredMixin, generic.edit.UpdateView):
    model = ProviderExpense
    form_class = ProviderExpenseForm
    template_name = 'events/expenses/provider_expense_form.html'
    permission_required = 'events.change_providerexpense'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context.
        context = super(ProviderExpenseUpdateView, self).get_context_data(**kwargs)
        event = self.get_object().event
        context['event'] = event
        return context

    def has_permission(self):
        ret = super(ProviderExpenseUpdateView, self).has_permission()
        # Must be event organizer.
        event = self.get_object().event
        if ret and not is_event_organizer(self.request.user, event):
            self.permission_denied_message = MUST_BE_EVENT_ORGANIZAER_MESSAGE
            return False
        # Cant change expense with payment
        if self.get_object().payment:
            self.permission_denied_message = CANT_CHANGE_PROVIDER_EXPENSE_WITH_PAYMENT
            return False
        return ret

    def handle_no_permission(self):
        message = self.get_permission_denied_message()
        if message == MUST_BE_EVENT_ORGANIZAER_MESSAGE:
            messages.add_message(self.request, messages.WARNING, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
            return redirect('event_list')
        elif message == CANT_CHANGE_PROVIDER_EXPENSE_WITH_PAYMENT:
            messages.add_message(
                self.request,
                messages.WARNING,
                CANT_CHANGE_PROVIDER_EXPENSE_WITH_PAYMENT
            )
            return redirect('provider_expense_detail', pk=self.get_object().pk)
            return False
        else:
            return super(ProviderExpenseUpdateView, self).handle_no_permission()


class ProviderExpenseSwitchState(PermissionRequiredMixin, View):
    permission_required = 'events.change_providerexpense'

    def post(self, request, *args, **kwargs):
        expense = get_object_or_404(Expense, pk=kwargs['pk'])
        if expense.cancelled_date:
            expense.cancelled_date = None
        else:
            expense.cancelled_date = timezone.now()
        expense.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            EXPENSE_MODIFIED
        )
        return redirect('provider_expense_detail', pk=expense.pk)


class OrganizerRefundSwitchState(PermissionRequiredMixin, View):
    permission_required = 'events.change_organizerrefund'

    def post(self, request, *args, **kwargs):
        expense = get_object_or_404(Expense, pk=kwargs['pk'])
        if expense.cancelled_date:
            expense.cancelled_date = None
        else:
            expense.cancelled_date = timezone.now()
        expense.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            EXPENSE_MODIFIED
        )
        return redirect('organizer_refund_detail', pk=expense.pk)


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
sponsoring_set_close = SponsoringSetClose.as_view()

sponsoring_invoice_create = InvoiceCreateView.as_view()
sponsoring_invoice_affect_create = InvoiceAffectCreateView.as_view()

invoice_set_approved = InvoiceSetAproved.as_view()
invoice_set_complete_payment = InvoiceSetCompletePayment.as_view()
invoice_set_partial_payment = InvoiceSetPartialPayment.as_view()

providers_list = ProvidersListView.as_view()
provider_detail = ProviderDetailView.as_view()
provider_change = ProviderChangeView.as_view()
provider_create = ProviderCreateView.as_view()

expenses_list = ExpensesListView.as_view()
provider_expense_create = ProviderExpenseCreateView.as_view()
provider_expense_update = ProviderExpenseUpdateView.as_view()
provider_expense_switch_state = ProviderExpenseSwitchState.as_view()
provider_expense_detail = ProviderExpenseDetailView.as_view()
provider_expense_payment_create = ProviderExpensePaymentCreateView.as_view()
organizer_refund_create = OrganizerRefundCreateView.as_view()
organizer_refund_detail = OrganizerRefundDetailView.as_view()
organizer_refund_payment_create = OrganizerRefundPaymentCreateView.as_view()
organizer_refund_switch_state = OrganizerRefundSwitchState.as_view()
