from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils.translation import ugettext_lazy as _
from events.helpers.permissions import (
    associate_users_permissions,
    super_organizer_permissions,
    organizer_permissions
)
from events.middleware import set_current_user
from events.models import (
    Event
)
from unittest import TestCase
User = get_user_model()

sponsor_data = {
    'organization_name': 'te patrocino',
    'document_number': '20-26456987-7',
    'vat_condition': 'monotributo',
    'contact_info': '',
    'address': ''
}

invoice_data = {
}

sponsor_categoty_data = {
    'name': 'Oro',
    'amount': '10000'
}


def _associate_organizer_perms(organizers_users):
    permissions = organizer_permissions()
    associate_users_permissions(organizers_users, permissions)


def _associate_super_organizer_perms(super_organizers_users):
    permissions = super_organizer_permissions()
    associate_users_permissions(super_organizers_users, permissions)


def create_user_set():
    """Create a organizer and superuser users."""
    organizers = []
    super_organizers = []

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
    """Create Events to test."""
    set_current_user(user)
    Event.objects.create(name='MyTest01', commission=10)
    Event.objects.create(name='MyTest02', commission=20)


def get_response_wsgi_messages(response):
    storage = get_messages(response.wsgi_request)
    return [message.message for message in storage]


class CustomAssertMethods(TestCase):

    def assertContainsMessage(self, response, message_text):
        messages = get_response_wsgi_messages(response)
        compare_messages = ((message == message_text) for message in messages)
        self.assertTrue(any(compare_messages),
                        _(f"Mensaje: '{message_text}' no encontrado en la lista de mensajes."))
