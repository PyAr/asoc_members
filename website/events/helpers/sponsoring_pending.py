"""Sponsoring helper.
This module is to help on construct the list of pending sponsoring.
    Organizer Tasks:
        * calculate_sponsoring_pending_by_organizer

    Superuser Tasks:
        * calculate_all_sponsoring_pending
"""
from django.urls import reverse
from events.constants import SPONSOR_STATE_CHECKED, SPONSOR_STATE_PARTIALLY_PAID
from events.models import Organizer, Sponsoring


class PendingSponsoring:
    """Represents a pending sponsoring asigned to organizer or user.
    Each as must have an event, description, amount and url.
    """
    def __init__(self, event, description, amount, url):
        self.event = event
        self.description = description
        self.amount = amount
        self.url = url


def pending_sponsoring(sponsoring):
    description = sponsoring.get_sponsoring_description
    event = sponsoring.sponsorcategory.event
    amount = sponsoring.sponsorcategory.amount
    url = reverse('sponsoring_detail', kwargs={'pk': sponsoring.pk})
    return PendingSponsoring(event, description, amount, url)


def calculate_all_sponsoring_pending():
    """Calculates all pending sponsoring.

    Returns:
    list(PendingSponsoring): List of all pending sponsoring
    """
    pending = []

    for sponsoring in Sponsoring.objects.all():
        if sponsoring.state == SPONSOR_STATE_PARTIALLY_PAID or \
           sponsoring.state == SPONSOR_STATE_CHECKED:
            pending.append(pending_sponsoring(sponsoring))
    pending.sort(key=lambda x: x.amount, reverse=True)
    return pending


def calculate_sponsoring_pending_by_organizer(organizer_user):
    """Calculates pending sponsoring by organizer.

    Parameters:
    organizer_user (User):  User that match with organizer

    Returns:
    list(PendingSponsoring): List of organizer pending sponsoring
    """
    pending = []
    organizer = Organizer.objects.get(user=organizer_user)
    for sponsoring in Sponsoring.objects.filter(
            sponsorcategory__event__in=organizer.get_associate_events()):
        if sponsoring.state == SPONSOR_STATE_PARTIALLY_PAID or \
           sponsoring.state == SPONSOR_STATE_CHECKED:
            pending.append(pending_sponsoring(sponsoring))
    pending.sort(key=lambda x: x.amount, reverse=True)
    return pending
