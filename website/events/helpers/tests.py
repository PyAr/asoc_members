from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.utils.translation import ugettext_lazy as _

from events.constants import CAN_VIEW_EVENT_ORGANIZERS_CODENAME, CAN_VIEW_ORGANIZERS_CODENAME
from events.models import Event, Organizer, EventOrganizer, SponsorCategory

from unittest import TestCase


def organizer_permissions():
    permissions = []
    event_content_type = ContentType.objects.get_for_model(Event)
    # Event update permmission.
    permissions.append(Permission.objects.get(
        content_type=event_content_type,
        codename='change_event')
    )

    event_content_type = ContentType.objects.get_for_model(SponsorCategory)
    # Sponsorcategory create permmission.
    permissions.append(Permission.objects.get(
        content_type=event_content_type,
        codename='add_sponsorcategory')
    )

    return permissions


def super_organizer_permissions():
    permissions = organizer_permissions()
    # Starts with organizer permissions.

    event_content_type = ContentType.objects.get_for_model(Event)
    organizer_content_type = ContentType.objects.get_for_model(Organizer)
    event_organizer_content_type = ContentType.objects.get_for_model(EventOrganizer)

    permissions.append(Permission.objects.get(content_type=event_content_type, codename='add_event'))
    # Event create permmission.
    permissions.append(Permission.objects.get(content_type=event_content_type,
                                              codename=CAN_VIEW_EVENT_ORGANIZERS_CODENAME))
    # Can view associated event organizers.

    permissions.append(Permission.objects.get(content_type=organizer_content_type,
                                              codename='add_organizer'))
    # Organizer create permmission.
    permissions.append(Permission.objects.get(content_type=organizer_content_type,
                                              codename='change_organizer'))
    # Organizer change permmission.
    permissions.append(Permission.objects.get(content_type=organizer_content_type,
                                              codename=CAN_VIEW_ORGANIZERS_CODENAME))
    # Can view organizers permmission.
    permissions.append(Permission.objects.get(content_type=organizer_content_type,
                                              codename='add_organizer'))
    # Organizer add permmission.
    permissions.append(Permission.objects.get(content_type=organizer_content_type,
                                              codename='change_organizer'))
    # Organizer update permmission.
    permissions.append(Permission.objects.get(content_type=event_organizer_content_type,
                                              codename='add_eventorganizer'))
    # EventOrganizer create permmission.
    permissions.append(Permission.objects.get(content_type=event_organizer_content_type,
                                              codename='change_eventorganizer'))
    # EventOrganizer update permmission.
    permissions.append(Permission.objects.get(content_type=event_organizer_content_type,
                                              codename='delete_eventorganizer'))
    # EventOrganizer delete permmission.
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
