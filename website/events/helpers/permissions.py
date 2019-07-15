from django.apps import apps
from events.constants import (
    CAN_CLOSE_SPONSORING_CODENAME,
    CAN_SET_APPROVED_INVOICE_CODENAME,
    CAN_SET_COMPLETE_PAYMENT_CODENAME,
    CAN_SET_PARTIAL_PAYMENT_CODENAME,
    CAN_SET_SPONSORS_ENABLED_CODENAME,
    CAN_VIEW_EVENT_ORGANIZERS_CODENAME,
    CAN_VIEW_EXPENSES_CODENAME,
    CAN_VIEW_ORGANIZERS_CODENAME,
    CAN_VIEW_PROVIDERS_CODENAME,
    CAN_VIEW_SPONSORS_CODENAME
)
from events.models import Organizer

Group = apps.get_model("auth", "Group")
Permission = apps.get_model("auth", "Permission")
ORGANIZER_GROUP_NAME = 'event_base_organizer'
# List of Organizer's permissions.
ORGANIZER_PERMISSIONS_CODENAMES = [
    'change_event',
    'add_sponsorcategory',
    'change_sponsorcategory',
    'delete_sponsorcategory',
    'add_bankaccountdata',
    'change_bankaccountdata',
    'add_sponsor',
    'change_sponsor',
    'add_sponsoring',
    'change_sponsoring',
    'delete_sponsoring',
    CAN_VIEW_SPONSORS_CODENAME,
    CAN_VIEW_PROVIDERS_CODENAME,
    CAN_VIEW_EVENT_ORGANIZERS_CODENAME,
    CAN_VIEW_EXPENSES_CODENAME,
    'add_invoiceaffect',
    'delete_invoiceaffect',
    CAN_SET_APPROVED_INVOICE_CODENAME,
    'add_expense',
    'add_provider',
    'change_provider',
    'add_providerexpense',
    'change_providerexpense',
    'change_expense',
    'add_organizerrefund',
    'change_organizerrefund'
]

# Initial only superuser has these permissions. But each perm check on view is added here to test
SUPER_ORGANIZER_PERMISSIONS_CODENAMES = [
    'add_event',
    'add_organizer',
    'change_organizer',
    CAN_VIEW_ORGANIZERS_CODENAME,
    'add_organizer',
    'add_eventorganizer',
    'change_eventorganizer',
    'delete_eventorganizer',
    CAN_SET_SPONSORS_ENABLED_CODENAME,
    CAN_CLOSE_SPONSORING_CODENAME,
    'add_invoice',
    CAN_SET_COMPLETE_PAYMENT_CODENAME,
    CAN_SET_PARTIAL_PAYMENT_CODENAME,
    'add_payment',
    'change_payment'
]


def organizer_permissions():
    permissions = []
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


def create_organizer_group():
    """
    create_organizer_group function:
    Idempotent function to create base_organizer group with perms. Usefull to use on
    commands an migrations.
    """
    organizer_group, created = Group.objects.get_or_create(name=ORGANIZER_GROUP_NAME)

    for codename in ORGANIZER_PERMISSIONS_CODENAMES:
        organizer_group.permissions.add(
            Permission.objects.get(content_type__app_label='events', codename=codename)
        )


def create_organizer_group_migrations_wrapped(apps, schema_editor):
    """" Wraping create_organizer_group function to can be use on migrations.RunPython"""
    # Group = apps.get_model("auth", "Group")
    # Permission = apps.get_model("auth", "Permission")
    create_organizer_group()


def remove_organizer_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    organizer_group = Group.objects.get(name=ORGANIZER_GROUP_NAME)
    organizer_group.delete()


def is_event_organizer(user, event):
    # Returns if a user is organizer of an event, or is a superuser.
    if not user.is_superuser:
        try:
            organizer = Organizer.objects.get(user=user)
        except Organizer.DoesNotExist:
            organizer = None
        if organizer and (organizer in event.organizers.all()):
            return True
        else:
            return False
    else:
        return True

    return False


def is_organizer_user(user):
    if Organizer.objects.filter(user=user).exists():
        return True
    else:
        return False
