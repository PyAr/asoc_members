from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.utils.translation import ugettext_lazy as _

from events.constants import (
    CAN_SET_SPONSORS_ENABLED_CODENAME,
    CAN_VIEW_EVENT_ORGANIZERS_CODENAME,
    CAN_VIEW_ORGANIZERS_CODENAME,
    CAN_VIEW_SPONSORS_CODENAME
)
from events.models import (
    Event,
    BankAccountData,
    Organizer,
    EventOrganizer,
    Sponsor,
    SponsorCategory
)

from unittest import TestCase

# List of Organizer's permissions.
ORGANIZER_PERMISSIONS_CODENAMES = [
    'change_event',
    'add_sponsorcategory',
    'add_bankaccountdata',
    'change_bankaccountdata',
    'add_sponsor',
    'change_sponsor',
    CAN_VIEW_SPONSORS_CODENAME
]

# Initial only superuser has these permissions. But each perm check on view is added here to test
SUPER_ORGANIZER_PERMISSIONS_CODENAMES = [
    'add_event',
    CAN_VIEW_EVENT_ORGANIZERS_CODENAME,
    'add_organizer',
    'change_organizer',
    CAN_VIEW_ORGANIZERS_CODENAME,
    'add_organizer',
    'add_eventorganizer',
    'change_eventorganizer',
    'delete_eventorganizer'
]


def organizer_permissions():
    permissions = []
    # Event update permmission.
    for codename in ORGANIZER_PERMISSIONS_CODENAMES:
        permissions.append(Permission.objects.get(
            content_type__app_label='events',
            codename=codename)
        )

    return permissions


def super_organizer_permissions():
    permissions = organizer_permissions()  # Starts with organizer permissions.

    for codename in SUPER_ORGANIZER_PERMISSIONS_CODENAMES:
        permissions.append(Permission.objects.get(content_type__app_label='events',
                                                  codename=codename))
    return permissions


def associate_users_permissions(users, permissions):
    for user in users:
        for permission in permissions:
            user.user_permissions.add(permission)


def get_response_wsgi_messages(response):
    storage = get_messages(response.wsgi_request)
    return [message.message for message in storage]


class CustomAssertMethods(TestCase):

    def assertContainsMessage(self, response, message_text):
        messages = get_response_wsgi_messages(response)
        compare_messages = ((message == message_text) for message in messages)
        self.assertTrue(any(compare_messages),
                        _(f"Mensaje: '{message_text}' no encontrado en la lista de mensajes."))
