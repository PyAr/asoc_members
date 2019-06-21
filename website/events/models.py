from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from events.helpers.models import AudithUserTime, SaveReversionMixin, ActiveManager
from events.constants import (
    CUIT_REGEX,
    CAN_CLOSE_SPONSORING_CODENAME,
    CAN_SET_APPROVED_INVOICE_CODENAME,
    CAN_SET_COMPLETE_PAYMENT_CODENAME,
    CAN_SET_PARTIAL_PAYMENT_CODENAME,
    CAN_SET_SPONSORS_ENABLED_CODENAME,
    CAN_VIEW_EVENT_ORGANIZERS_CODENAME,
    CAN_VIEW_ORGANIZERS_CODENAME,
    CAN_VIEW_SPONSORS_CODENAME,
    IMAGE_FORMATS,
    SPONSOR_STATE_CHECKED,
    SPONSOR_STATE_CLOSED,
    SPONSOR_STATE_COMPLETELY_PAID,
    SPONSOR_STATE_INVOICED,
    SPONSOR_STATE_PARTIALLY_PAID,
    SPONSOR_STATE_UNBILLED
)

from members.models import DEFAULT_MAX_LEN, LONG_MAX_LEN
import os
import reversion

User = get_user_model()


def lower_non_spaces(text):
    return text.lower().replace(' ', '')


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

    def __str__(self):
        return (
            f"{self.get_category_display()} "
            f"- {self.name} "
            f"({self.place})"
        )

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

    def __str__(self):
        return f"{self.event.name} ( {self.name} )"

    class Meta:
        unique_together = ('event', 'name')


@reversion.register
class Sponsoring(SaveReversionMixin, AudithUserTime):
    """
    Sponsoring:
    Represents the many to many relationship between SponsorCategory and Sponsors. Is important
    had this relation as model to payment fks, etc."""
    sponsorcategory = models.ForeignKey(
        'SponsorCategory',
        related_name='sponsor_by',
        on_delete=models.CASCADE
    )
    sponsor = models.ForeignKey(
        'Sponsor',
        related_name='sponsoring',
        on_delete=models.CASCADE
    )
    comments = models.TextField(_('comentarios'), blank=True)
    close = models.BooleanField(_('cerrado'), default=False)

    def __str__(self):
        return (
            f"{self.sponsor.organization_name} "
            f"- {self.sponsorcategory.event.name} "
            f"({self.sponsorcategory.name})"
        )

    def get_absolute_url(self):
        return reverse('sponsoring_detail', args=[str(self.pk)])

    @property
    def state(self):
        # TODO: to not use so many "if" can write a decision matriz.
        current_state = SPONSOR_STATE_UNBILLED
        if self.close:
            return SPONSOR_STATE_CLOSED

        if hasattr(self, 'invoice'):
            invoice = self.invoice
            current_state = SPONSOR_STATE_INVOICED
            if invoice.invoice_ok:
                current_state = SPONSOR_STATE_CHECKED
                if invoice.partial_payment:
                    current_state = SPONSOR_STATE_PARTIALLY_PAID
                if invoice.complete_payment:
                    current_state = SPONSOR_STATE_COMPLETELY_PAID

        return current_state

    class Meta:
        unique_together = ('sponsorcategory', 'sponsor')
        permissions = (
            (CAN_CLOSE_SPONSORING_CODENAME, _('puede cerrar patrocinio')),
        )


@reversion.register
class Sponsor(SaveReversionMixin, AudithUserTime):
    """Represents a sponsor. The active atributte is like a soft deletion."""

    RESPONSABLE_INSCRIPTO = 'responsable inscripto'
    MONOTRIBUTO = 'monotributo'
    CONSUMIDOR_FINAL = 'consumidor final'
    EXTERIOR = 'exterior'
    OTRO = 'otro'

    VAT_CONDITIONS_CHOICES = (
        (RESPONSABLE_INSCRIPTO, 'Responsable Inscripto'),
        (MONOTRIBUTO, 'Monotributo'),
        (CONSUMIDOR_FINAL, 'Consumidor Final'),
        (EXTERIOR, 'Exterior'),
        (OTRO, 'Otro'),
    )

    enabled = models.BooleanField(_('habilitado'), default=False)
    active = models.BooleanField(_('activo'), default=True)

    organization_name = models.CharField(
        _('razón social'),
        max_length=DEFAULT_MAX_LEN,
        help_text=_('Razón social.')
    )
    document_number = models.CharField(
        _('CUIT'),
        max_length=13,
        help_text=_('CUIT, formato ##-########-#'),
        validators=[RegexValidator(CUIT_REGEX, _('El CUIT ingresado no es correcto.'))],
        unique=True
    )

    contact_info = models.TextField(_('información de contacto'), blank=True)

    address = models.CharField(
        _('direccion'),
        max_length=LONG_MAX_LEN,
        help_text=_('Dirección'),
        blank=True
    )

    vat_condition = models.CharField(
        _('condición frente al iva'),
        max_length=DEFAULT_MAX_LEN,
        choices=VAT_CONDITIONS_CHOICES
    )

    other_vat_condition_text = models.CharField(
        _('otra condicion frente al iva'),
        max_length=DEFAULT_MAX_LEN,
        blank=True,
        default='',
        help_text=_('Especifica otra condición frente al iva'),
    )
    # Overrinding objects to explicit when need to show inactive objects.
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        permissions = (
            (CAN_SET_SPONSORS_ENABLED_CODENAME, _('puede habilitar patrocinadores')),
            (CAN_VIEW_SPONSORS_CODENAME, _('puede ver patrocinadores')),
        )
        ordering = ['-created']

    def __str__(self):
        return f"{self.organization_name} - {self.document_number}"

    def get_absolute_url(self):
        return reverse('sponsor_detail', args=[str(self.pk)])


def invoice_upload_path(instance, filename):
    """
    Customize the incoice's upload path to
    MEDIA_ROOT/events/invoices/event_sponsor_category_document.ext.
    """
    ext = filename.split('.')[-1]
    sponsor_name = lower_non_spaces(instance.sponsoring.sponsor.organization_name)
    event_name = lower_non_spaces(instance.sponsoring.sponsorcategory.event.name)
    sponsor_categoty_name = lower_non_spaces(instance.sponsoring.sponsorcategory.name)

    return (
        f"media/events/invoices/"
        f"{event_name}_{sponsor_name}_{sponsor_categoty_name}.{ext}"
    )


@reversion.register
class Invoice(SaveReversionMixin, AudithUserTime):
    amount = models.DecimalField(_('monto'), max_digits=18, decimal_places=2)
    partial_payment = models.BooleanField(_('pago parcial'), default=False)
    complete_payment = models.BooleanField(_('pago completo'), default=False)
    observations = models.CharField(_('observaciones'), max_length=LONG_MAX_LEN, blank=True)
    document = models.FileField(_('archivo'), upload_to=invoice_upload_path)
    invoice_ok = models.BooleanField(_('Factura generada OK'), default=False)
    sponsoring = models.OneToOneField(
        'Sponsoring',
        related_name='invoice',
        verbose_name=_('patrocinio'),
        on_delete=models.SET_NULL,
        null=True
    )

    def invoice_affects_total_sum(self):
        sum = self.invoice_affects.all().aggregate(total=Sum('amount'))
        return sum['total']

    def extension(self):
        name, extension = os.path.splitext(self.document.name)
        return extension

    def clean(self):
        if self.partial_payment and self.complete_payment:
            raise ValidationError(
                _('los atributos partial_payment (pago parcial) y complete_payment '
                  '(pago completo) no pueden estar ambos seteados en Verdadero')
            )

    def is_image_document(self):
        return self.extension() in IMAGE_FORMATS

    class Meta:
        permissions = (
            (CAN_SET_APPROVED_INVOICE_CODENAME, _('puede aprobar factura')),
            (CAN_SET_COMPLETE_PAYMENT_CODENAME, _('puede setear pago completo')),
            (CAN_SET_PARTIAL_PAYMENT_CODENAME, _('puede setear pago parcial')),
        )


def affect_upload_path(instance, filename):
    """
    Customize the invoice affect's upload path to
    MEDIA_ROOT/events/invoices_affect/event_sponsor_category_document_affectcategory_pk.ext.
    """
    ext = filename.split('.')[-1]
    sponsor_name = lower_non_spaces(instance.invoice.sponsoring.sponsor.organization_name)
    event_name = lower_non_spaces(instance.invoice.sponsoring.sponsorcategory.event.name)
    sponsor_categoty_name = lower_non_spaces(instance.invoice.sponsoring.sponsorcategory.name)

    return (
        f"media/events/invoices_affect/"
        f"{event_name}_{sponsor_name}_{sponsor_categoty_name}"
        f"_{instance.category}{instance.pk}.{ext}"
    )


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
        on_delete=models.CASCADE,
        related_name='invoice_affects'
    )

    document = models.FileField(_('archivo'), upload_to=affect_upload_path, blank=True)

    category = models.CharField(
        _('tipo'), max_length=5, choices=TYPE_CHOICES
    )

    def extension(self):
        name, extension = os.path.splitext(self.document.name)
        return extension

    def is_image_document(self):
        return self.extension() in IMAGE_FORMATS
