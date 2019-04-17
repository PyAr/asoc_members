from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from members.models import DEFAULT_MAX_LEN, LONG_MAX_LEN

User = get_user_model()

class BankAccountData(TimeStampedModel):
    """Account data for monetary transerences."""
    #TODO: regex validator for cuit
    document_number = models.CharField(_('CUIT'), max_length=13, 
        help_text=_('CUIT del propietario de la cuenta')
    )

    bank_entity = models.CharField(
        _('entidad bancaria'), 
        max_length=DEFAULT_MAX_LEN, 
        help_text=_('nombre de la entiedad bancaria')
    )
    #TODO: Some validator??
    cbu = models.CharField(_('CBU'), max_length=DEFAULT_MAX_LEN)


class Organizer(TimeStampedModel):
    """Organizer, person asigned to administrate events."""
    first_name = models.CharField(_('nombre'), max_length=DEFAULT_MAX_LEN)
    last_name = models.CharField(_('apellido'), max_length=DEFAULT_MAX_LEN)
    
    user = models.OneToOneField(
        User,
        verbose_name=_('usuario'),
        on_delete=models.CASCADE
    )

    account_data = models.ForeignKey(
        'BankAccountData',
        verbose_name=_('datos cuenta bancaria'), 
        on_delete=models.CASCADE, 
        null=True
    )


class Event(TimeStampedModel):
    """A representation of an Event."""
    PYDAY = 'PD'
    PYCON = 'PCo'
    PYCAMP = 'PCa'
    PYCONF = 'Con'
    TYPE_CHOICES = (
        (PYDAY, 'PyDay'),
        (PYCON, 'PyCon'),
        (PYCAMP, 'PyCamp'),
        (PYCONF, 'Conferencia')
    )
    name = models.CharField(_('nombre'), max_length=DEFAULT_MAX_LEN)
    
    commission = models.DecimalField(
        _('comisión'), 
        max_digits=5, 
        decimal_places=2,
        validators=[MaxValueValidator(100), MinValueValidator(0)]
    )

    start_date = models.DateField(_('fecha de incio'), blank=True, null=True)
    place = models.CharField(_('lugar'), max_length=DEFAULT_MAX_LEN, blank=True)
    category = models.CharField(
        _('tipo'), max_length=3, choices=TYPE_CHOICES)

    organizers =  models.ManyToManyField(
        'Organizer',
        verbose_name=_('organizadores'),
        related_name='events'
    )

    def add_organizer(self, organizer):
        """Add new organizer.
        Using it instead direct add, is better to run other task like send mails.
        """
        #TODO
        pass
