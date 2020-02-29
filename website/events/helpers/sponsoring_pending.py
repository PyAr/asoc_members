"""Sponsoring helper.
This module is to help on construct the list of pending sponsoring.
    Organizer Tasks:
        * calculate_sponsoring_pending_by_organizer

    Superuser Tasks:
        * calculate_all_sponsoring_pending
"""
from collections import namedtuple

from django.urls import reverse
from events.constants import SPONSOR_STATE_CHECKED, SPONSOR_STATE_PARTIALLY_PAID
from events.models import Organizer, Sponsoring


PendingSponsoring = namedtuple('PendingSponsoring', 'description, amount, url')


def pending_sponsoring(sponsoring):
    description = f"{sponsoring} - {sponsoring.state.upper()}"
    amount = sponsoring.sponsorcategory.amount
    url = reverse('sponsoring_detail', kwargs={'pk': sponsoring.pk})
    return PendingSponsoring(description, amount, url)


def calculate_sponsoring_pending(organizer_user=False):
    """Calculates all pending sponsoring.

    Returns:
    list(PendingSponsoring): List of all pending sponsoring
    """
    pending = []
    if organizer_user:
        organizer = Organizer.objects.get(user=organizer_user)
        sponsorings = Sponsoring.objects.filter(
            sponsorcategory__event__in=organizer.get_associate_events())
    else:
        sponsorings = Sponsoring.objects.all()

    for sponsoring in sponsorings:
        if sponsoring.state == SPONSOR_STATE_PARTIALLY_PAID or \
           sponsoring.state == SPONSOR_STATE_CHECKED:
            pending.append(pending_sponsoring(sponsoring))
        pending.sort(key=lambda x: x.amount, reverse=True)
    return pending
