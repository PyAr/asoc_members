from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files import File
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from events.helpers.permissions import (
    associate_users_permissions,
    super_organizer_permissions,
    organizer_permissions
)
from events.middleware import set_current_user
from events.models import (
    Event,
    EventOrganizer,
    Invoice,
    InvoiceAffect,
    Organizer,
    Sponsor,
    SponsorCategory,
    Sponsoring,
    Provider,
    OrganizerRefund,
    ProviderExpense,
)
from unittest import TestCase, mock

User = get_user_model()


sponsor_data = {
    'organization_name': 'te patrocino',
    'document_number': '20-36436060-7',
    'vat_condition': 'monotributo',
    'contact_info': '',
    'address': ''
}

invoice_data = {
    'amount': '20000'
}

provider_data = {
    'organization_name': 'Pablo',
    'document_number': '20364360607',
    'bank_entity': 'Banco Rio',
    'account_type': 'CC',
    'account_number': '4',
    'cbu': '0720403020000000914086'
}


def _associate_organizer_perms(organizers_users):
    permissions = organizer_permissions()
    associate_users_permissions(organizers_users, permissions)


def _associate_super_organizer_perms(super_organizers_users):
    permissions = super_organizer_permissions()
    associate_users_permissions(super_organizers_users, permissions)


def create_user_set():
    """Create users set to test.

    Postcondition:
    A set of 6 user will be created with the next pursposes:
    noOrganizer: user without perms or organizer association
    organizer01, organizer02, , organizer03: three simple user to associate organizer perms
    superOrganizer01: user to test perms that are not from simple organizer
    administrator: super user
    """

    organizers = []
    super_organizers = []

    User.objects.create_user(
        username="noOrganizer",
        email="noOrganizer@test.com",
        password="noOrganizer"
    )

    organizers.append(User.objects.create_user(
        username="organizer01",
        email="test01@test.com",
        password="organizer01"
    ))
    organizers.append(User.objects.create_user(
        username="organizer02",
        email="test02@test.com",
        password="organizer02"
    ))
    organizers.append(User.objects.create_user(
        username="organizer03",
        email="test03@test.com",
        password="organizer03"
    ))
    super_organizers.append(User.objects.create_user(
        username="superOrganizer01",
        email="super01@test.com",
        password="superOrganizer01"
    ))
    # Created to test perms without use superuser.
    User.objects.create_superuser(
        username="administrator",
        email="admin@test.com",
        password="administrator"
    )

    _associate_organizer_perms(organizers)
    _associate_super_organizer_perms(super_organizers)


def create_event_set(user):
    """Create events set to test.

    Args:
    user -- existing User

    Postcondition:
    Two Events created by user with: comission 10 and 20.
    Gold and Silver SponsorCategory associated to events
    """
    set_current_user(user)
    event01 = Event.objects.create(name='MyTest01', commission=10)
    Event.objects.create(name='MyTest02', commission=20)

    SponsorCategory.objects.create(name='Gold', amount=10000, event=event01)
    SponsorCategory.objects.create(name='Silver', amount=1000, event=event01)
    return event01


def create_organizer_set(auto_create_user_set=False):
    """Create organizers set to test.

    Args:
    auto_create_user_set -- flag tindicating that create_user_set function must be executed

    Precondition:
    create_user_set

    Postcondition:
    Two Organizers created associated to users organizer01, and organizer02.
    Not events association.
    """
    if auto_create_user_set:
        create_user_set()

    set_current_user(User.objects.get(username="administrator"))

    Organizer.objects.bulk_create([
        Organizer(user=User.objects.get(username="organizer01"), first_name="Organizer01"),
        Organizer(user=User.objects.get(username="organizer02"), first_name="Organizer02"),
        Organizer(user=User.objects.get(username="organizer03"), first_name="Organizer03")
    ])


def associate_events_organizers():
    """Create associations between Events and Organizers.

    Precondition:
    Users, Organizers and Events must be created, at least by the functions:
    create_user_set, create_organizer_set and create_event_set

    Postcondition:
    MyTest01 event associated with organizer01 and organizer02
    MyTest02 event associated with organizer02
    organizer03 has not events associated
    """
    event01 = Event.objects.filter(name='MyTest01').first()
    event02 = Event.objects.filter(name='MyTest02').first()
    organizer01 = Organizer.objects.get(user__username='organizer01')
    organizer02 = Organizer.objects.get(user__username='organizer02')

    EventOrganizer.objects.bulk_create([
        EventOrganizer(event=event01, organizer=organizer01),
        EventOrganizer(event=event01, organizer=organizer02),
        EventOrganizer(event=event02, organizer=organizer02)
    ])


def create_sponsors_set():
    """Create Sponsors set to test.

    Postcondition:
    creates two sponsor one is enabled and the other not.
    """
    Sponsor.objects.create(**sponsor_data)
    Sponsor.objects.create(
        organization_name='EnabledSponsor',
        document_number='20-26456987-8',
        vat_condition='monotributo',
        enabled=True)


def create_provider():
    return Provider.objects.create(**provider_data)


def create_sponsoring_set(auto_create_sponsors_set=False):
    """Create sponsoring set to test.

    Args:
    auto_create_sponsors_set -- flag tindicating that create_sponsors_set function must be executed

    Precondition:
    create_sponsors_set

    Postcondition:
    sponsoring created for a enabled sponsor and sponsorcategory1 that is associated with event1
    """
    if auto_create_sponsors_set:
        create_sponsors_set()

    event = Event.objects.filter(name='MyTest01').first()
    Sponsoring.objects.create(
        sponsor=Sponsor.objects.filter(enabled=True).first(),
        sponsorcategory=SponsorCategory.objects.filter(event=event).first()
    )


def create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=False):
    """Create sponsoring invoice to test.

    Args:
    auto_create_sponsoring_and_sponsor -- flag tindicating that create_sponsoring_set function
    must be executed

    Precondition:
    create_sponsoring_set

    Postcondition:
    invoice created for an unclose sponsoring associate with sponsorcategory1 that is associated
    with event1
    """
    invoice_file_mock = mock.MagicMock(spec=File, name='InvoiceMock')
    invoice_file_mock.name = 'invoice.pdf'

    if auto_create_sponsoring_and_sponsor:
        create_sponsoring_set(auto_create_sponsors_set=True)

    event = Event.objects.filter(name='MyTest01').first()
    sponsoring = Sponsoring.objects.filter(
        close=False,
        sponsorcategory=SponsorCategory.objects.filter(event=event).first()
    ).first()
    invoice = Invoice(amount=10000, sponsoring=sponsoring, document=invoice_file_mock)
    with mock.patch('django.core.files.storage.FileSystemStorage.save') as mock_save:
        mock_save.return_value = 'invoice.pdf'
        invoice.save()

    return invoice


def create_invoice_affect_set(invoice, total_amount=False):
    InvoiceAffect.objects.create(amount=1000, invoice=invoice, category='Pay')
    InvoiceAffect.objects.create(amount=1000, invoice=invoice, category='Hold')
    if total_amount:
        InvoiceAffect.objects.create(amount=invoice.amount, invoice=invoice, category='Hold')


def get_response_wsgi_messages(response):
    storage = get_messages(response.wsgi_request)
    return [message.message for message in storage]


def create_provider_expense(payment=None, cancelled_date=None):
    """Create provider expense to test.

    Precondition:
        create_sponsoring_invoice()
        create_event_set()
        create_provider()
    """
    provider = Provider.objects.first()
    if provider is None:
        provider = create_provider()
    event = Event.objects.first()
    if event is None:
        event = create_event_set()
    return ProviderExpense.objects.create(
        provider=provider,
        amount='1200',
        invoice_type='A',
        invoice_date=timezone.now(),
        description='test',
        event=event,
        cancelled_date=cancelled_date,
        payment=payment,
    )


def create_organizer_refund():
    """Create organizer refund to test.

    Precondition:
        create_sponsoring_invoice()
        create_event_set()
        create_organizer()
    """
    OrganizerRefund.objects.create(
        organizer=Organizer.objects.first(),
        amount='1200',
        invoice_type='A',
        invoice_date=timezone.now(),
        description='test',
        event=Event.objects.first(),
        cancelled_date=None,
    )


class CustomAssertMethods(TestCase):

    def assertContainsMessage(self, response, message_text):
        messages = get_response_wsgi_messages(response)
        compare_messages = ((message == message_text) for message in messages)
        self.assertTrue(any(compare_messages),
                        _(f"Mensaje: '{message_text}' no encontrado en la lista de mensajes."))

    def assertForbidden(self, response):
        self.assertEqual(response.status_code, 403)
