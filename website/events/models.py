from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from members.models import DEFAULT_MAX_LEN, LONG_MAX_LEN
from .constants import CUIT_REGEX, CAN_VIEW_ORGANIZERS_CODENAME

User = get_user_model()

class BankAccountData(TimeStampedModel):
    """Account data for monetary transerences."""
    #TODO: regex validator for cuit
    document_number = models.CharField(_('CUIT'), max_length=13, 
        help_text=_('CUIT del propietario de la cuenta'), 
        validators=[RegexValidator(CUIT_REGEX, _('El CUIT ingresado no es correcto'))]
    )

    bank_entity = models.CharField(
        _('entidad bancaria'), 
        max_length=DEFAULT_MAX_LEN, 
        help_text=_('nombre de la entiedad bancaria')
    )
    account_number =  models.CharField(_('número de cuenta'), max_length=13, help_text=_('Número de cuenta'))
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

    @property
    def email(self):
        return self.user.email
    
    def __str__(self):
        return f"{ self.user.username } - {self.email}"


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
        _('tipo'), max_length=3, choices=TYPE_CHOICES, blank=True)

    organizers =  models.ManyToManyField(
        'Organizer',
        through='EventOrganizer',
        verbose_name=_('organizadores'),
        related_name='events'
    )

    def associate_organizer(self, organizer, notify=False):
        """Add new organizer.
        Using it instead direct add, is better to run other task like send mails.
        """
        EventOrganizer.objects.create(event=self, organizer=organizer)
        if notify:
            mail_account = organizer.user.email
            #TODO: send mail to organizer??. Model is to low, better on view

    class Meta:
        permissions = (
            (CAN_VIEW_ORGANIZERS_CODENAME,_('puede ver organizadores')),
        )
        ordering = ['start_date'] 



class EventOrganizer(TimeStampedModel):
    """Represents the many to many relationship between events and organizers. With TimeStamped
    is easy to kwon when a user start as organizer from an event, etc"""
    event = models.ForeignKey('Event', related_name='event_organizers', on_delete=models.CASCADE)
    organizer = models.ForeignKey('Organizer', related_name='organizer_events', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('event','organizer')
    

class SponsorCategory(TimeStampedModel):
    name = models.CharField(_('nombre'), max_length=DEFAULT_MAX_LEN)
    amount = models.DecimalField(_('monto'), max_digits=18, decimal_places=2)
    event = models.ForeignKey(
        'Event',
        verbose_name=_('Evento'), 
        on_delete=models.CASCADE, 
        related_name='sponsors_categories'
    )
