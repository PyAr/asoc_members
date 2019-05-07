from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from events.constants import CAN_VIEW_ORGANIZERS_CODENAME
from events.models import Event, Organizer, EventOrganizer, SponsorCategory

def organizer_permissions():
    permissions = []
    event_content_type = ContentType.objects.get_for_model(Event)
    #event update permmission
    permissions.append(Permission.objects.get(content_type=event_content_type, codename='change_event'))
    
    event_content_type = ContentType.objects.get_for_model(SponsorCategory)
    #sponsorcategory create permmission
    permissions.append(Permission.objects.get(content_type=event_content_type, codename='add_sponsorcategory'))

    return permissions

def super_organizer_permissions():
    permissions = organizer_permissions()
    # Starts with organizer permissions.

    event_content_type = ContentType.objects.get_for_model(Event)
    organizer_content_type = ContentType.objects.get_for_model(Organizer)
    event_organizer_content_type = ContentType.objects.get_for_model(EventOrganizer)
    
    permissions.append(Permission.objects.get(content_type=event_content_type, codename='add_event'))
    # Event create permmission.
    permissions.append(Permission.objects.get(content_type=event_content_type, codename=CAN_VIEW_ORGANIZERS_CODENAME))
    # Can view associated event organizers 

    permissions.append(Permission.objects.get(content_type=organizer_content_type, codename='add_organizer'))
    # Organizer create permmission.
    permissions.append(Permission.objects.get(content_type=organizer_content_type, codename='change_organizer'))
    # Organizer change permmission.

    permissions.append(Permission.objects.get(content_type=organizer_content_type, codename='add_organizer'))
    # Organizer add permmission.
    permissions.append(Permission.objects.get(content_type=organizer_content_type, codename='change_organizer'))
    # Organizer update permmission.

    permissions.append(Permission.objects.get(content_type=event_organizer_content_type, codename='add_eventorganizer'))
    # EventOrganizer create permmission.
    permissions.append(Permission.objects.get(content_type=event_organizer_content_type, codename='change_eventorganizer'))
    # EventOrganizer update permmission.
    permissions.append(Permission.objects.get(content_type=event_organizer_content_type, codename='delete_eventorganizer'))
    # EventOrganizer delete permmission.
    return permissions


def associate_users_permissions(users, permissions):
    for user in users:
        for permission in permissions:
            user.user_permissions.add(permission)