from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.models import TimeStampedModel


DEFAULT_MAX_LEN = 317  # Almost random
LONG_MAX_LEN = 2048  # Random but bigger


class Member(TimeStampedModel):
    """Base Model for the Membership to the ONG. People and Organizations can be members."""

    legal_id = models.PositiveIntegerField(_('ID legal'), unique=True)
    registration_date = models.DateField(_('fecha de alta'))

    category = models.ForeignKey(
        'Category',
        verbose_name=_('categoría'),
        null=True,
        on_delete=models.SET_NULL,
        related_name='members'
    )
    patron = models.ForeignKey(  # This is the person that pays for this Member's subscription
        'Patron',
        verbose_name=_('mecenas'),
        null=True,
        on_delete=models.SET_NULL,
        related_name='beneficiary'
    )
    # Flags
    has_student_certificate = models.BooleanField(_('tiene certificado de estudiante?'), default=False)
    has_subscription_letter = models.BooleanField(_('ha firmado la carta?'), default=False)

    def __str__(self):
        return f"{str(self.legal_id).zfill(5)} - {self.person}"


class Person(TimeStampedModel):
    """Human being, member of PyAr ONG."""

    first_name = models.CharField(_('nombre'), max_length=DEFAULT_MAX_LEN)
    last_name = models.CharField(_('apellido'), max_length=DEFAULT_MAX_LEN)

    membership = models.OneToOneField(
        'Member',
        verbose_name=_('membresía'),
        null=True,
        on_delete=models.SET_NULL
    )

    document_number = models.CharField(_('N° de documento'), max_length=DEFAULT_MAX_LEN, blank=True)
    email = models.EmailField(_('correo electrónico'), max_length=1024)
    nickname = models.CharField(_('nick'), max_length=DEFAULT_MAX_LEN, blank=True, help_text=_('Nick o sobrenombre'))
    picture = models.ImageField(
        _('avatar'), upload_to='pictures', null=True,
        help_text=_('Foto o imagen cuadrada para el carnet'))
    nationality = models.CharField(_('nacionalidad'), max_length=DEFAULT_MAX_LEN, blank=True)
    marital_status = models.CharField(_('estado civil'), max_length=DEFAULT_MAX_LEN, blank=True)
    occupation = models.CharField(_('profesión'), max_length=DEFAULT_MAX_LEN, blank=True, help_text=_('Profesión o ocupación'))
    birth_date = models.DateField(_('fecha de nacimiento'), null=True, blank=True)
    street_address = models.CharField(_('dirección'), max_length=DEFAULT_MAX_LEN, blank=True)
    zip_code = models.CharField(_('código postal'), max_length=DEFAULT_MAX_LEN, blank=True)
    city = models.CharField(_('ciudad'), max_length=DEFAULT_MAX_LEN, blank=True)
    province = models.CharField(_('provincia'), max_length=DEFAULT_MAX_LEN, blank=True)
    country = models.CharField(_('país'), max_length=DEFAULT_MAX_LEN, blank=True)

    comments = models.TextField(_('comentarios'), blank=True)

    @property
    def full_name(self):
        return str(self)  # We may want a different representation of str(self) changes

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"


class Organization(TimeStampedModel):
    """Organization (legal), member of the ONG."""
    name = models.CharField(_('nombre'), max_length=DEFAULT_MAX_LEN, blank=True)
    contact_info = models.TextField(_('información de contacto'), blank=True)
    document_number = models.CharField(_('CUIT'), max_length=DEFAULT_MAX_LEN, blank=True,
                                       help_text='CUIT o equivalencia')

    membership = models.OneToOneField(
        'Member',
        verbose_name=_('membresía'),
        null=True,
        on_delete=models.SET_NULL,
        related_name='organization'
    )

    address = models.CharField(_('dirección'), max_length=LONG_MAX_LEN, blank=True)
    social_media = models.TextField(_('redes sociales'), blank=True)


class Category(TimeStampedModel):
    """Membership category."""
    name = models.CharField(_('nombre'), max_length=DEFAULT_MAX_LEN)
    description = models.TextField(_('descipción'), )
    fee = models.DecimalField(_('cuota mensual'), max_digits=18, decimal_places=2)
    # There is a foreign keys to Membership

    def __str__(self):
        return self.name


class Patron(TimeStampedModel):
    """Somebody that pays a Membership fee.
    Either for an Organization or Person, who may or may not be himself.

    """
    name = models.CharField(_('nombre'), max_length=DEFAULT_MAX_LEN)
    email = models.EmailField(_('correo electrónico'), max_length=1024, unique=True)
    comments = models.TextField(_('comentarios'), blank=True)

    def __str__(self):
        return self.name


class PaymentStrategy(TimeStampedModel):
    """This class models the different ways that there are to pay for a membership."""

    MERCADO_PAGO = 'mercado pago'
    PLATFORM_CHOICES = (
        (MERCADO_PAGO, 'Mercado Pago'),
        ('todo pago', 'Todo Pago'),
        ('transfer', 'transferencia bancaria'),
    )

    platform = models.CharField(_('plataforma'), max_length=DEFAULT_MAX_LEN, choices=PLATFORM_CHOICES,
                                default=MERCADO_PAGO)
    id_in_platform = models.CharField(_('ID de plataforma'), max_length=DEFAULT_MAX_LEN)
    comments = models.TextField(_('comentarios'), blank=True)
    patron = models.ForeignKey('Patron', verbose_name=_('mecenas'),  on_delete=models.SET_NULL, null=True)


class Payment(TimeStampedModel):
    """Record a pay event."""

    timestamp = models.DateTimeField(_('fecha y hora'))
    amount = models.DecimalField(_('monto'), max_digits=18, decimal_places=2)
    strategy = models.ForeignKey('PaymentStrategy', verbose_name=_('estrategia de pago'),  on_delete=models.SET_NULL, null=True)
    comments = models.TextField(_('comentarios'), blank=True)


class Quota(TimeStampedModel):
    """Like cuota in Spanish... exactly that. A monthly fee some member pays."""

    payment = models.ForeignKey('Payment', verbose_name=_('pago'),  on_delete=models.CASCADE)
    month = models.PositiveSmallIntegerField(
        _('mes'), validators=[MaxValueValidator(12), MinValueValidator(1)])
    year = models.PositiveSmallIntegerField(_('año'), validators=[MinValueValidator(2015)])
    amount = models.DecimalField(_('monto'), max_digits=18, decimal_places=2)
    member = models.ForeignKey('Member', verbose_name=_('miembro'),  on_delete=models.SET_NULL, null=True)
    invoice_id = models.CharField(_('ID de factura'), max_length=DEFAULT_MAX_LEN, blank=True)
