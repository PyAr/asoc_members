from django.utils.translation import gettext_lazy as _


# Permissions codenames to create groups, asign, and test.
CAN_CLOSE_SPONSORING_CODENAME = 'close_sponsoring'
CAN_VIEW_EVENT_ORGANIZERS_CODENAME = 'view_event_organizers'
CAN_VIEW_ORGANIZERS_CODENAME = 'view_organizers'
CAN_VIEW_EVENTS_CODENAME = 'view_events'
CAN_VIEW_SPONSORS_CODENAME = 'view_sponsors'
CAN_VIEW_EXPENSES_CODENAME = 'view_expenses'
CAN_VIEW_PROVIDERS_CODENAME = 'view_providers'
CAN_SET_SPONSORS_ENABLED_CODENAME = 'set_sponsors_enabled'
CAN_SET_APPROVED_INVOICE_CODENAME = 'set_invoice_approved'
CAN_SET_COMPLETE_PAYMENT_CODENAME = 'set_invoice_complete_payment'
CAN_SET_PARTIAL_PAYMENT_CODENAME = 'set_invoice_partial_payment'

# Messages constants, to use on views and test.
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
    "No se puede modificar un evento cerrado. Pida a un administrador que vuelva "
    "a abrirlo, desde el administrador de eventos."
)

ORGANIZER_MAIL_NOTOFICATION_MESSAGE = _(
    'Se le envio un mail al usuario organizador para que pueda '
    'ingresar sus credenciales de autenticación'
)

DUPLICATED_SPONSOR_CATEGORY_MESSAGE = _(
    'Ya tiene registrada una categoria de sponsor con este '
    'nombre para el evento actual. '
    'Las categorias de sponsor para un evento deben ser únicas.'
)

MUST_BE_APPROVED_INVOICE_MESSAGE = _(
    'La factura debe estar aprobada para poder realizar la acción seleccionada'
)

MUST_EXISTS_SPONSOR_MESSAGE = _(
    'No se puede asociar patrocinios sin sponsors habilitados'
)

MUST_EXISTS_SPONSOR_CATEGORY_MESSAGE = _(
    'No se puede asociar patrocinios sin categorias de sponsor en el evento'
)

MUST_EXISTS_PROVIDERS_MESSAGE = _(
    'No se puede crear un gasto de proveedor sin antes dar de alta proveedores'
)

CANT_CHANGE_PROVIDER_EXPENSE_WITH_PAYMENT = _(
    'No se puede modificar un gasto con pago asociado al mismo'
)

INVOICE_APPOVED_MESSAGE = _('Factura aprobada exitosamente ')

INVOICE_SET_COMPLETE_PAYMENT_MESSAGE = _('Factura marcada como pago completo ')

INVOICE_SET_PARTIAL_PAYMENT_MESSAGE = _('Factura marcada como pago parcial ')

SPONSORING_SUCCESSFULLY_CLOSE_MESSAGE = _('Patrocinio cerrado exitosamente')

EXPENSE_MODIFIED = _('Gasto modificado exitosamente')

# Sponsoring/invoice states
SPONSOR_STATE_UNBILLED = _('no facturado')
SPONSOR_STATE_INVOICED = _('facturado')
SPONSOR_STATE_CHECKED = _('pendiente de pago')
SPONSOR_STATE_PARTIALLY_PAID = _('pago parcial')
SPONSOR_STATE_COMPLETELY_PAID = _('pago completo')
SPONSOR_STATE_CLOSED = _('cerrado')

# The idea is have formats supported by img tag
IMAGE_FORMATS = ['.jpeg', '.jpg', '.gif', '.png', '.svg', '.bmp']
DEFAULT_PAGINATION = 15
BIG_PAGINATION = 20
