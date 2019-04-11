from django.utils.translation import gettext_lazy as _

ATTRIBUTE_SIMILARITY_HELP = _("La contrsaña no puede ser similar a tu otra información personal.")
COMMON_PASSWORD_HELP = _("La contraseña no puede ser comunmente usada.")
NUMERIC_PASSWORD_HELP = _("La constraseña no puede contener solo números.")
MINIMUM_LENGTH_HELP = _("La contraseña debe contener al menos 8 caracteres.")

PASSWORD_VALIDATOR_HELP_TEXTS = [
    ATTRIBUTE_SIMILARITY_HELP,
    COMMON_PASSWORD_HELP,
    NUMERIC_PASSWORD_HELP,
    MINIMUM_LENGTH_HELP,
    ]