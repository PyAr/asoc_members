from django.utils.translation import gettext_lazy as _

"""Helping constant for validate passwords."""
ATTRIBUTE_SIMILARITY_HELP = _("La contraseña no puede ser similar a su otra información personal.")
COMMON_PASSWORD_HELP = _("La contraseña no puede ser comunmente usada.")
NUMERIC_PASSWORD_HELP = _("La constraseña no puede contener solo números.")
MINIMUM_LENGTH_HELP = _("La contraseña debe contener al menos 8 caracteres.")

PASSWORD_VALIDATOR_HELP_TEXTS = [
    ATTRIBUTE_SIMILARITY_HELP,
    COMMON_PASSWORD_HELP,
    NUMERIC_PASSWORD_HELP,
    MINIMUM_LENGTH_HELP,
    ]

CUIT_REGEX =r'^(20|23|24|27|30|33|34)-[0-9]{8}-[0-9]$'

"""Permissions codenames to create groups, asign, and test."""
CAN_ASSOCIATE_ORGANIZER_CODENAME = 'add_eventorganizer'
CAN_VIEW_ORGANIZERS_CODENAME = 'view_organizers'