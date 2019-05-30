from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from events.helpers.models import AudithUserTime, SaveReversionMixin, ActiveManager
from events.constants import (
    CUIT_REGEX,
    CAN_VIEW_EVENT_ORGANIZERS_CODENAME,
    CAN_VIEW_ORGANIZERS_CODENAME,
    CAN_VIEW_SPONSORS_CODENAME
)

from members.models import DEFAULT_MAX_LEN, LONG_MAX_LEN
import os
import reversion

User = get_user_model()


@reversion.register
class BankAccountData(SaveReversionMixin, AudithUserTime):
    """Account data for monetary transferences."""
    CC = 'CC'
    CA = 'CA'
    ACCOUNT_TYPE_CHOICES = (
        (CC, 'Cuenta corriente'),
        (CA, 'Caja de ahorros')
    )
    document_number = models.CharField(
        _('CUIT'),
        max_length=13,
        help_text=_('CUIT del propietario de la cuenta, formato ##-########-#'),
        validators=[RegexValidator(CUIT_REGEX, _('El CUIT ingresado no es correcto.'))]
    )

    bank_entity = models.CharField(
        _('entidad bancaria'),
        max_length=DEFAULT_MAX_LEN,
        help_text=_('Nombre de la entiedad bancaria.')
    )
    account_number = models.CharField(
        _('número de cuenta'),
        max_length=13,
        help_text=_('Número de cuenta.')
    )
    account_type = models.CharField(_('Tipo cuenta'), max_length=3, choices=ACCOUNT_TYPE_CHOICES)

    organization_name = models.CharField(
        _('razón social'),
        max_length=DEFAULT_MAX_LEN,
        help_text=_('Razón social o nombre del propietario de la cuenta.')
    )
    cbu = models.CharField(_('CBU'), max_length=DEFAULT_MAX_LEN, help_text=_('CBU de la cuenta'))

    def is_owner(self, organizer):
        '''Returns if the organizer is the owner of the current account.'''
        return organizer in self.organizer_set.all()


@reversion.register
class Organizer(SaveReversionMixin, AudithUserTime):
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

    def get_absolute_url(self):
        return reverse('organizer_detail', args=[str(self.pk)])

    class Meta:
        permissions = (
            (CAN_VIEW_ORGANIZERS_CODENAME, _('puede ver organizadores')),
        )
        ordering = ['-created']


@reversion.register
class Event(SaveReversionMixin, AudithUserTime):
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

    organizers = models.ManyToManyField(
        'Organizer',
        through='EventOrganizer',
        verbose_name=_('organizadores'),
        related_name='events'
    )

    close = models.BooleanField(_('cerrado'), default=False)

    def get_absolute_url(self):
        return reverse('event_detail', args=[str(self.pk)])

    class Meta:
        permissions = (
            (CAN_VIEW_EVENT_ORGANIZERS_CODENAME, _('puede ver organizadores del evento')),
        )
        ordering = ['-start_date'] 


@reversion.register
class EventOrganizer(SaveReversionMixin, AudithUserTime):
    """Represents the many to many relationship between events and organizers. With TimeStamped
    is easy to kwon when a user start as organizer from an event, etc."""
    event = models.ForeignKey('Event', related_name='event_organizers', on_delete=models.CASCADE)
    organizer = models.ForeignKey(
        'Organizer',
        related_name='organizer_events',
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ('event', 'organizer')


@reversion.register
class SponsorCategory(SaveReversionMixin, AudithUserTime):
    name = models.CharField(_('nombre'), max_length=DEFAULT_MAX_LEN)
    amount = models.DecimalField(_('monto'), max_digits=18, decimal_places=2)
    event = models.ForeignKey(
        'Event',
        verbose_name=_('Evento'),
        on_delete=models.CASCADE,
        related_name='sponsors_categories'
    )

    sponsors = models.ManyToManyField(
        'Sponsor',
        through='Sponsoring',
        verbose_name=_('patrocinios'),
        related_name='sponsor_categories'
    )
    class Meta:
        unique_together = ('event', 'name')


@reversion.register
class Sponsoring(SaveReversionMixin, AudithUserTime):
    """
    Sponsoring:
    Represents the many to many relationship between SponsorCategory and Sponsors. Is important
    had this relation as model to payment fks, etc."""
    sponsorcategory = models.ForeignKey('SponsorCategory', related_name='sponsor_by', on_delete=models.CASCADE)
    sponsor = models.ForeignKey(
        'Sponsor',
        related_name='sponsoring',
        on_delete=models.CASCADE
    )
    comments = models.TextField(_('comentarios'), blank=True)


@reversion.register
class Sponsor(SaveReversionMixin, AudithUserTime):
    """Represents a sponsor. The active atributte is like a soft deletion."""

    """VAT conditions from: https://github.com/WhyNotHugo/django-afip."""
    # http://www.afip.gov.ar/afip/resol1415_anexo2.html
    VAT_CONDITIONS = (
        'IVA Responsable Inscripto',
        'IVA Responsable No Inscripto',
        'IVA Exento',
        'No Responsable IVA',
        'Responsable Monotributo',
    )
    CLIENT_VAT_CONDITIONS = (
        'IVA Responsable Inscripto',
        'IVA Responsable No Inscripto',
        'IVA Sujeto Exento',
        'Consumidor Final',
        'Responsable Monotributo',
        'Proveedor del Exterior',
        'Cliente del Exterior',
        'IVA Liberado - Ley Nº 19.640',
        'IVA Responsable Inscripto - Agente de Percepción',
        'Monotributista Social',
        'IVA no alcanzado',
    )

    VAT_CONDITIONS_CHOICES = ((cond, cond) for cond in CLIENT_VAT_CONDITIONS)

    enabled = models.BooleanField(_('cerrado'), default=False)
    active = models.BooleanField(_('cerrado'), default=True)
    
    organization_name = models.CharField(
        _('razón social'),
        max_length=DEFAULT_MAX_LEN,
        help_text=_('Razón social.')
    )
    document_number = models.CharField(
        _('CUIT'),
        max_length=13,
        help_text=_('CUIT, formato ##-########-#'),
        validators=[RegexValidator(CUIT_REGEX, _('El CUIT ingresado no es correcto.'))]
    )

    contact_info = models.TextField(_('información de contacto'), blank=True)

    address = models.CharField(
        _('direccion'),
        max_length=LONG_MAX_LEN,
        help_text=_('Dirección')
    )
    
    vat_condition = models.CharField(
        _('condición frente al iva'),
        max_length=48,
        choices=VAT_CONDITIONS_CHOICES
    )
    # Overrinding objects to explicit when need to show inactive objects.
    objects = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"{self.organization_name} - {self.document_number}"


@reversion.register
class Invoice(SaveReversionMixin, AudithUserTime):
    amount = models.DecimalField(_('monto'), max_digits=18, decimal_places=2)
    partial_payment = models.BooleanField(_('pago parcial'), default=False)
    complete_payment = models.BooleanField(_('pago completo'), default=False)
    close = models.BooleanField(_('cerrado'), default=True)
    observations = models.CharField(_('observaciones'), max_length=LONG_MAX_LEN, blank=True)
    file = models.FileField(_('archivo'), upload_to='invoices/documments/')
    # TODO: clean partial and complete not true at same time


@reversion.register
class InvoiceAffect(SaveReversionMixin, AudithUserTime):
    PAYMENT = 'Pay'
    WITHHOLD = 'Hold'
    OTHER = 'Oth'
    TYPE_CHOICES = (
        (PAYMENT, 'Pago'),
        (WITHHOLD, 'Retencion'),
        (OTHER, 'Otros')
    )
    
    amount = models.DecimalField(_('monto'), max_digits=18, decimal_places=2)
    observations = models.CharField(_('observaciones'), max_length=LONG_MAX_LEN, blank=True)
    invoice = models.ForeignKey(
        'Invoice',
        verbose_name=_('factura'), 
        on_delete=models.CASCADE 
    )

    file = models.FileField(_('archivo'), upload_to='invoice_affects/documments/')

    category = models.CharField(
        _('tipo'), max_length=5, choices=TYPE_CHOICES)
