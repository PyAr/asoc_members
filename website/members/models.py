from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel


DEFAULT_MAX_LEN = 317  # Almost random
LONG_MAX_LEN = 2048  # Random but bigger


class Member(TimeStampedModel):
    """Base Model for the Membership to the ONG. People and Organizations can be members."""

    legal_id = models.PositiveIntegerField(unique=True)
    registration_date = models.DateField()

    category = models.ForeignKey(
        'Category',
        null=True,
        on_delete=models.SET_NULL,
        related_name='members'
    )
    patron = models.ForeignKey(  # This is the person that pays for this Member's subscription
        'Patron',
        null=True,
        on_delete=models.SET_NULL,
        related_name='beneficiary'
    )
    # Flags
    has_student_certificate = models.BooleanField(default=False)
    has_subscription_letter = models.BooleanField(default=False)

    def __str__(self):
        return f"{str(self.legal_id).zfill(5)} - {self.person}"


class Person(TimeStampedModel):
    """Human being, member of PyAr ONG."""

    first_name = models.CharField(max_length=DEFAULT_MAX_LEN)
    last_name = models.CharField(max_length=DEFAULT_MAX_LEN)

    membership = models.OneToOneField(
        'Member',
        null=True,
        on_delete=models.SET_NULL,
        related_name='person'
    )

    document_number = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
    email = models.EmailField(max_length=1024)
    nickname = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
    picture = models.ImageField(null=True)
    nationality = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
    marital_status = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
    occupation = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    street_address = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
    zip_code = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
    city = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
    province = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
    country = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)


    def __str__(self):
        return f"{self.last_name}, {self.first_name}"


class Organization(TimeStampedModel):
    """Organization (legal), member of the ONG."""
    name = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
    contact_info = models.TextField(blank=True)
    document_number = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True,
                                       help_text='CUIT, etc.')

    membership = models.OneToOneField(
        'Member',
        null=True,
        on_delete=models.SET_NULL,
        related_name='organization'
    )

    address = models.CharField(max_length=LONG_MAX_LEN, blank=True)
    social_media = models.TextField(blank=True)


class Category(TimeStampedModel):
    """Membership category."""
    name = models.CharField(max_length=DEFAULT_MAX_LEN)
    description = models.TextField()
    fee = models.DecimalField(max_digits=18, decimal_places=2)
    # There is a foreign keys to Membership


class Patron(TimeStampedModel):
    """Somebody that pays a Membership fee.
    Either for an Organization or Person, who may or may not be himself.

    """
    name = models.CharField(max_length=DEFAULT_MAX_LEN)
    email = models.EmailField(max_length=1024)
    comments = models.TextField(blank=True)


class PaymentStrategy(TimeStampedModel):
    """This class models the different ways that there are to pay for a membership."""

    MERCADO_PAGO = 'mercado pago'
    PLATFORM_CHOICES = (
        (MERCADO_PAGO, 'Mercado Pago'),
        ('todo pago', 'Todo Pago'),
        ('transfer', 'transferencia bancaria'),
    )

    platform = models.CharField(max_length=DEFAULT_MAX_LEN, choices=PLATFORM_CHOICES,
                                default=MERCADO_PAGO)
    id_in_platform = models.CharField(max_length=DEFAULT_MAX_LEN)
    comments = models.TextField(blank=True)
    patron = models.ForeignKey('Patron', on_delete=models.SET_NULL, null=True)


class Payment(TimeStampedModel):
    """Record a pay event."""

    timestamp = models.DateTimeField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    strategy = models.ForeignKey('PaymentStrategy', on_delete=models.SET_NULL, null=True)
    comments = models.TextField(blank=True)


class Quota(TimeStampedModel):
    """Like cuota in Spanish... exactly that. A monthly fee some member pays."""

    payment = models.ForeignKey('Payment', on_delete=models.CASCADE)
    month = models.PositiveSmallIntegerField(validators=[MaxValueValidator(12),
                                                         MinValueValidator(1)])
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(2015)])
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    member = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True)
    invoice_id = models.CharField(max_length=DEFAULT_MAX_LEN, blank=True)
