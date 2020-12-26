from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.templatetags.static import static

DEFAULT_MAX_LEN = 317  # Almost random
LONG_MAX_LEN = 2048  # Random but bigger


class Quota(TimeStampedModel):
    """Like cuota in Spanish... exactly that. A monthly fee some member pays."""

    payment = models.ForeignKey('Payment', verbose_name=_('pago'), on_delete=models.CASCADE)
    month = models.PositiveSmallIntegerField(
        _('mes'), validators=[MaxValueValidator(12), MinValueValidator(1)])
    year = models.PositiveSmallIntegerField(_('año'), validators=[MinValueValidator(2015)])
    member = models.ForeignKey(
        'Member', verbose_name=_('miembro'), on_delete=models.SET_NULL, null=True)

    class Meta:
        get_latest_by = ['year', 'month']

    def __str__(self):
        return "<Quota {}-{} payment={}".format(self.year, self.month, self.payment)

    @property
    def code(self):
        return f'{self.year}-{self.month:02d}'

    @classmethod
    def decode(cls, code):
        return int(code[:2]), int(code[2:])

    @classmethod
    def code_from_date(cls, when):
        return when.strftime('%y%m')


class Member(TimeStampedModel):
    """Base Model for the Membership to the ONG. People and Organizations can be members."""

    legal_id = models.PositiveIntegerField(_('ID legal'), unique=True, blank=True, null=True)
    registration_date = models.DateField(_('fecha de alta'), blank=True, null=True)
    shutdown_date = models.DateField(_('fecha de baja'), blank=True, null=True)

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
        blank=True,
        on_delete=models.SET_NULL,
        related_name='beneficiary'
    )
    first_payment_month = models.PositiveSmallIntegerField(
        _('primer pago mes'), validators=[MaxValueValidator(12), MinValueValidator(1)],
        null=True, blank=True)
    first_payment_year = models.PositiveSmallIntegerField(
        _('primer pago año'), validators=[MinValueValidator(2015)], null=True, blank=True)

    # Flags
    has_student_certificate = models.BooleanField(
        _('tiene certificado de estudiante?'), default=False)
    has_subscription_letter = models.BooleanField(_('ha firmado la carta?'), default=False)
    has_collaborator_acceptance = models.BooleanField(
        _('ha aceptado ser colaborador?'), default=False)

    @property
    def entity(self):
        """Return the Person or Organization for the member, if any."""
        try:
            return self.person
        except Person.DoesNotExist:
            pass

        try:
            return self.organization
        except Organization.DoesNotExist:
            pass

    def __str__(self):
        legal_id = "∅" if self.legal_id is None else f'{self.legal_id:05d}'
        shutdown = "" if self.shutdown_date is None else ", DADO DE BAJA"
        return f"{legal_id} - [{self.category}{shutdown}] {self.entity}"

    def get_missing_info(self, for_approval=False):
        """Indicate in which categories the member is missing something.

        If `for_approval` is indicated, some data will not be reported as missing (as they
        are not really needed for legal approval).
        """
        cat_student = Category.objects.get(name=Category.STUDENT)
        cat_collab = Category.objects.get(name=Category.COLLABORATOR)

        # simple flags with "Not Applicable" situation
        missing_student_certif = (
            self.category == cat_student and not self.has_student_certificate)
        missing_collab_accept = (
            self.category == cat_collab and not self.has_collaborator_acceptance)

        # info from Person
        missing_nickname = self.person.nickname == ""
        # picture is complicated, bool() is used to check if the Image field has an associated
        # filename, and False itself is used as the "dont want a picture!" flag
        missing_picture = not self.person.picture and self.person.picture is not False

        # info from Member itself
        missing_payment = self.first_payment_month is None and self.category.fee > 0
        missing_signed_letter = not self.has_subscription_letter

        # some fields are not really needed to for a member to be legally approved
        if for_approval:
            missing_nickname = False
            missing_picture = False
            missing_payment = False

        return {
            'missing_signed_letter': missing_signed_letter,
            'missing_student_certif': missing_student_certif,
            'missing_payment': missing_payment,
            'missing_nickname': missing_nickname,
            'missing_picture': missing_picture,
            'missing_collab_accept': missing_collab_accept,
        }


def picture_upload_path(instance, filename):
    """Customize the picture's upload path to MEDIA_ROOT/pictures/lastname_document.ext."""
    ext = filename.split('.')[-1]
    lastname = instance.last_name.lower().replace(' ', '')
    return f"pictures/{lastname}_{instance.document_number}.{ext}"


def validate_image_ratio(obj):
    width, height = get_image_dimensions(obj)
    if width != height:
        raise ValidationError("Por favor, utilice una imagen cuadrada")


class Person(TimeStampedModel):
    """Human being, member of PyAr ONG."""

    first_name = models.CharField(_('nombre'), max_length=DEFAULT_MAX_LEN)
    last_name = models.CharField(_('apellido'), max_length=DEFAULT_MAX_LEN)

    membership = models.OneToOneField(
        'Member',
        verbose_name=_('membresía'),
        related_name='person',
        on_delete=models.CASCADE,
    )

    document_number = models.CharField(
        _('N° de documento'), max_length=DEFAULT_MAX_LEN, null=False, unique=True)
    email = models.EmailField(_('correo electrónico'), max_length=1024)
    nickname = models.CharField(
        _('nick'), max_length=DEFAULT_MAX_LEN, blank=True, help_text=_('Nick o sobrenombre'))
    # picture in "False" means that the person doesn't want a photo (can not use Null as it's
    # swallowed by ImageField to disassociate from a filename)
    picture = models.ImageField(
        _('avatar'), validators=[validate_image_ratio], upload_to=picture_upload_path,
        null=True, blank=True, help_text=_('Foto o imagen cuadrada para el carnet'))
    nationality = models.CharField(_('nacionalidad'), max_length=DEFAULT_MAX_LEN, blank=True)
    marital_status = models.CharField(_('estado civil'), max_length=DEFAULT_MAX_LEN, blank=True)
    occupation = models.CharField(
        _('profesión'), max_length=DEFAULT_MAX_LEN, blank=True,
        help_text=_('Profesión o ocupación'))
    birth_date = models.DateField(_('fecha de nacimiento'), null=True, blank=True)
    street_address = models.CharField(_('dirección'), max_length=DEFAULT_MAX_LEN, blank=True)
    zip_code = models.CharField(_('código postal'), max_length=DEFAULT_MAX_LEN, blank=True)
    city = models.CharField(_('ciudad'), max_length=DEFAULT_MAX_LEN, blank=True)
    province = models.CharField(_('provincia'), max_length=DEFAULT_MAX_LEN, blank=True)
    country = models.CharField(_('país'), max_length=DEFAULT_MAX_LEN, blank=True)

    comments = models.TextField(_('comentarios'), blank=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def address(self):
        return f"{self.street_address}, {self.city} ({self.zip_code}), {self.province}"

    @property
    def thumbnail(self):
        if self.picture:
            photo = self.picture.url
        else:
            photo = static("images/default_thumbnail.jpg")
        return format_html(
            f'<a href="{photo}"><img src="{photo}" \
                    class="img-thumbnail" width="150"></a>')

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

    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    """Membership category."""
    ACTIVE = "Activo"
    SUPPORTER = "Adherente"
    STUDENT = "Estudiante"
    COLLABORATOR = "Colaborador"
    TEENAGER = "Cadete"
    BENEFACTOR_PLATINUM = "Benefactora Platino"
    BENEFACTOR_GOLD = "Benefactora Oro"
    BENEFACTOR_SILVER = "Benefactora Plata"
    CATEGORY_CHOICES = (
        (ACTIVE, ACTIVE),
        (SUPPORTER, SUPPORTER),
        (STUDENT, STUDENT),
        (COLLABORATOR, COLLABORATOR),
        (TEENAGER, TEENAGER),
        (BENEFACTOR_PLATINUM, BENEFACTOR_PLATINUM),
        (BENEFACTOR_GOLD, BENEFACTOR_GOLD),
        (BENEFACTOR_SILVER, BENEFACTOR_SILVER),
    )
    HUMAN_CATEGORIES = {ACTIVE, SUPPORTER, STUDENT, COLLABORATOR, TEENAGER}

    class Meta:
        verbose_name_plural = "categories"

    name = models.CharField(
        _('nombre'), max_length=DEFAULT_MAX_LEN, choices=CATEGORY_CHOICES)
    description = models.TextField(_('descripción'), )
    fee = models.DecimalField(_('cuota mensual'), max_digits=18, decimal_places=2)
    # There is a foreign keys to Membership

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, Category):
            other_name = other.name
        elif isinstance(other, str):
            other_name = other
        else:
            return False

        return self.name == other_name


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
    TODO_PAGO = 'todo pago'
    TRANSFER = 'transfer'
    CREDIT = 'credit'
    PLATFORM_CHOICES = (
        (MERCADO_PAGO, 'Mercado Pago'),
        (TODO_PAGO, 'Todo Pago'),
        (TRANSFER, 'Transferencia Bancaria'),
        (CREDIT, 'Crédito Bonificado'),
    )

    platform = models.CharField(
        _('plataforma'), max_length=DEFAULT_MAX_LEN,
        choices=PLATFORM_CHOICES, default=MERCADO_PAGO)
    id_in_platform = models.CharField(_('ID de plataforma'), max_length=DEFAULT_MAX_LEN)
    comments = models.TextField(_('comentarios'), blank=True)
    patron = models.ForeignKey(
        'Patron', verbose_name=_('mecenas'), on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.patron} ({self.platform})'

    @property
    def platform_name(self):
        return dict(self.PLATFORM_CHOICES)[self.platform]


class Payment(TimeStampedModel):
    """Record a pay event."""

    timestamp = models.DateTimeField(_('fecha y hora'))
    amount = models.DecimalField(_('monto'), max_digits=18, decimal_places=2)
    strategy = models.ForeignKey(
        'PaymentStrategy', verbose_name=_('estrategia de pago'),
        on_delete=models.SET_NULL, null=True)
    comments = models.TextField(_('comentarios'), blank=True)

    # invoice selling point and number inside it, and if it was generated ok
    invoice_spoint = models.PositiveIntegerField(_('Punto de venta'), blank=True, null=True)
    invoice_number = models.PositiveIntegerField(_('Número de factura'), blank=True, null=True)
    invoice_ok = models.BooleanField(_('Factura generada OK'), default=False)

    class Meta:
        get_latest_by = ['timestamp']
        unique_together = ('invoice_spoint', 'invoice_number')

    def __str__(self):
        return f"<Payment {self.amount} [{self.timestamp}] from {self.strategy}>"
