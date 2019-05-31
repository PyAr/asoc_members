from django.utils.translation import gettext_lazy as _

CUIT_REGEX = r'^(20|23|24|27|30|33|34)-[0-9]{8}-[0-9]$'

"""Permissions codenames to create groups, asign, and test."""
CAN_VIEW_EVENT_ORGANIZERS_CODENAME = 'view_event_organizers'
CAN_VIEW_ORGANIZERS_CODENAME = 'view_organizers'
CAN_VIEW_EVENTS_CODENAME = 'view_events'
CAN_VIEW_SPONSORS_CODENAME = 'view_sponsors'
CAN_SET_SPONSORS_ENABLED_CODENAME = 'set_sponsors_enabled'

"""Messages constants, to use on views and test."""
MUST_BE_EVENT_ORGANIZAER_MESSAGE = _(
    'Para poder acceder a detalles del evento debe ser organizador del mismo.'
)

MUST_BE_ACCOUNT_OWNER_MESSAGE = _(
    'Para poder modificar los datos de la cuenta debe ser dueño de la misma.'
)

MUST_BE_ORGANIZER_MESSAGE = _(
    'Para realizar la acción requerida debe ser un organizador registrado.'
)

CANT_CHANGE_CLOSE_EVENT_MESSAGE = _(
    "No se puede modificar un evento cerrado. Pida a un administrador que vuelva" +
    " a abrirlo, desde el administrador de eventos."
)

ORGANIZER_MAIL_NOTOFICATION_MESSAGE = _(
    'Se le envio un mail al usuario organizador para que pueda '+
    'ingresar sus credenciales de autenticación'
)

DUPLICATED_SPONSOR_CATEGORY_MESSAGE = _(
    'Ya tiene registrada una categoria de sponsor con este ' +
    'nombre para el evento actual. ' +
    'Las categorias de sponsor para un evento deben ser únicas.'
)