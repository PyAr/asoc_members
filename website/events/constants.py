from django.utils.translation import gettext_lazy as _

CUIT_REGEX =r'^(20|23|24|27|30|33|34)-[0-9]{8}-[0-9]$'

"""Permissions codenames to create groups, asign, and test."""
CAN_VIEW_EVENT_ORGANIZERS_CODENAME = 'view_event_organizers'
CAN_VIEW_ORGANIZERS_CODENAME = 'view_organizers'
CAN_VIEW_EVENTS_CODENAME = 'view_events'
CAN_VIEW_SPONSORS_CODENAME = 'view_sponsors'

"""Messages constants, to use on views and test."""
MUST_BE_EVENT_ORGANIZAER_MESSAGE = _('Para poder acceder a detalles del evento debe ser organizador del mismo.')
CANT_CHANGE_CLOSE_EVENT_MESSAGE = _("No se puede modificar un evento cerrado. Pida a un administrador que vuelva" +
    " a abrirlo, desde el administrador de eventos.")