"""Task helper.
This module is to help on construct the list of pending tasks.
The idea is represents the next set of task types:
    Organizer Tasks:
        * Event with incomplete data (place, date or type) - INCOMPLETE_EVENT
        * Event without sponsorcategories - NOT_SPONSOR_CAEGORY
        * Invoice without approving - NOT_APPROVED_INVOICE
        * Personal data not updated - INCOMPLETE_PERSONAL_DATA
        * Missing Bank Account Data - NOT_BANK_ACCOUNT

    Superuser Tasks:
        * Sponsor not enabled
        * Invoice without set complete or partial payment
        * Sponsoring without invoice attached
        * Sponsoring with invoice affect that sum total invoice and not complete flag setted
"""
from django.urls import reverse
from events.models import Invoice, Organizer, SponsorCategory

INCOMPLETE_EVENT = 'incomplete_event'
NOT_SPONSOR_CAEGORY = 'not_sponsor_category'
NOT_APPROVED_INVOICE = 'not_approved_invoice'
INCOMPLETE_PERSONAL_DATA = 'incomplete_personal_data'
NOT_BANK_ACCOUNT = 'not_bank_account'


class Task:
    """Represents a pending task to asing a superuser or organizer.
    Each tas must have a description to show, an url to access to resolve
    and a time to order the group of tasks.
    """
    def __init__(self, description, url, time):
        self.description = description
        self.time = time
        self.url = url


class TaskFactory:
    """ Factory of task."""
    def __init__(self):
        self._builders = {}

    def register_builder(self, key, builder):
        self._builders[key] = builder

    def create(self, key, **kwargs):
        builder = self._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)


def incomplete_event_task_builder(event):
    description = f'El evento: "{event}", no tiene toda la informacion completa'
    url = reverse('event_change', kwargs={'pk': event.pk})
    time = event.modified
    return Task(description, url, time)


def not_sponsor_category_task_builder(event):
    description = f'El evento: "{event}", no tiene categorias de sponsor cargadas'
    url = reverse('event_detail', kwargs={'pk': event.pk})
    time = event.modified
    return Task(description, url, time)


def not_approved_invoices_task_builder(invoice):
    description = f'Falta aprobar la factura correspondiente al patrocinio: "{invoice.sponsoring}"'
    url = reverse('sponsoring_detail', kwargs={'pk': invoice.sponsoring.pk})
    time = invoice.created
    return Task(description, url, time)


def not_complete_personal_data_task_builder(organizer):
    description = f'Falta completar su informacion personal'
    url = reverse('organizer_change', kwargs={'pk': organizer.pk})
    time = organizer.created
    return Task(description, url, time)


def not_account_data_task_builder(organizer):
    description = f'Falta completar sus datos de cuenta bancaria'
    url = reverse('organizer_create_bank_account_data', kwargs={'pk': organizer.pk})
    time = organizer.created
    return Task(description, url, time)


factory = TaskFactory()
factory.register_builder(INCOMPLETE_EVENT, incomplete_event_task_builder)


def calculate_super_user_task():
    """Calculates superuser pending tasks.
    The user is not an argument because is the same for all superusers

    Returns:
    list(Task): List of superusar task
    """
    NotImplementedError('Not implemented error')


def calculate_organizer_task(organizer_user):
    """Calculates organizer pending tasks.

    Parameters:
    organizer_use (User):  User that match with organizer

    Returns:
    list(Task): List of organizer task
    """
    tasks = []
    organizer = Organizer.objects.get(user=organizer_user)

    # Incomplete events.
    incomplete_events = _incomoplete_events(organizer)
    for event in incomplete_events:
        tasks.append(incomplete_event_task_builder(event))

    # Events not incomplete and without any sponsorcategory.
    not_sponsor_events = _not_sponsor_category(organizer, incomplete_events)
    for event in not_sponsor_events:
        tasks.append(not_sponsor_category_task_builder(event))

    # Not approved invoices.
    not_approved_invoices = _not_approved_invoices(organizer)
    for invoice in not_approved_invoices:
        tasks.append(not_approved_invoices_task_builder(invoice))

    if not organizer.has_complete_personal_data():
        tasks.append(not_complete_personal_data_task_builder(organizer))
    else:
        if not organizer.has_account_data():
            tasks.append(not_account_data_task_builder(organizer))

    tasks.sort(key=lambda x: x.time, reverse=True)
    return tasks


def _incomoplete_events(organizer):
    ret = []
    for event in organizer.get_associate_events().all():
        if not event.has_complete_data():
            ret.append(event)
    return ret


def _not_sponsor_category(organizer, exclude_events):
    ret = []
    for event in organizer.get_associate_events().all():
        if (
            (event not in exclude_events) and
            (not SponsorCategory.objects.filter(event=event).exists())
        ):
            ret.append(event)

    return ret


def _not_approved_invoices(organizer):
    invoices = Invoice.objects.filter(
        invoice_ok=False,
        sponsoring__close=False,
        sponsoring__sponsorcategory__event__in=organizer.get_associate_events()
    )
    return invoices.all()
