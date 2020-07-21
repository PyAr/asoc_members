import math
import pytz
from random import choice

import factory
import factory.fuzzy
from factory.django import DjangoModelFactory
from faker import Faker

from members.models import (
    Category,
    Member,
    Organization,
    Patron,
    Payment,
    PaymentStrategy,
    Person,
    Quota,
)

fake = Faker("es_MX")


class PatronFactory(DjangoModelFactory):
    name = fake.name
    email = fake.email
    comments = fake.text

    class Meta:
        model = Patron
        django_get_or_create = ("name",)


class MemberFactory(DjangoModelFactory):
    legal_id = factory.fuzzy.FuzzyInteger(1, 99999999)
    has_student_certificate = fake.pybool
    has_subscription_letter = fake.pybool
    has_collaborator_acceptance = fake.pybool
    category = factory.Iterator(Category.objects.all())
    patron = factory.SubFactory(PatronFactory)
    first_payment_month = factory.fuzzy.FuzzyInteger(1, 12)
    first_payment_year = factory.fuzzy.FuzzyInteger(2010, 2025)

    @factory.lazy_attribute
    def registration_date(self):
        date_start = fake.past_date(start_date="-5y", tzinfo=None)
        return fake.date_between_dates(date_start=date_start)

    class Meta:
        model = Member
        django_get_or_create = ("legal_id",)


class OrganizationFactory(DjangoModelFactory):
    name = fake.company
    contact_info = fake.phone_number
    document_number = factory.fuzzy.FuzzyInteger(90000000, 99999999)
    address = fake.street_address
    social_media = fake.uri
    membership = factory.SubFactory(MemberFactory)

    class Meta:
        model = Organization
        django_get_or_create = ("name",)


class PersonFactory(DjangoModelFactory):
    first_name = fake.first_name
    last_name = fake.last_name
    membership = factory.SubFactory(MemberFactory)
    document_number = factory.fuzzy.FuzzyInteger(9_000_000, 99_999_999)
    email = fake.email
    street_address = fake.street_address
    nationality = fake.country
    marital_status = factory.Iterator(['casadx', 'solterx', 'viudx'])
    occupation = fake.job
    street_address = fake.street_address
    zip_code = factory.fuzzy.FuzzyInteger(1000, 9999)
    city = fake.city
    province = fake.state
    country = fake.country
    comments = fake.text

    class Meta:
        model = Person
        django_get_or_create = ("document_number",)

    @factory.lazy_attribute
    def birth_date(self):
        date_start = fake.past_date(start_date="-35y", tzinfo=None)
        return fake.date_between_dates(date_start=date_start)

    @factory.lazy_attribute
    def nickname(self):
        return fake.profile()["username"]


class PaymentStrategyFactory(DjangoModelFactory):
    platform = factory.LazyAttribute(lambda x: choice(PaymentStrategy.PLATFORM_CHOICES)[0])
    id_in_platform = factory.fuzzy.FuzzyText(length=24)
    comments = fake.text
    patron = factory.Iterator(Patron.objects.all())

    class Meta:
        model = PaymentStrategy
        django_get_or_create = ("patron",)


class PaymentFactory(DjangoModelFactory):
    strategy = factory.Iterator(PaymentStrategy.objects.all())
    comments = fake.text
    invoice_spoint = 7
    invoice_number = factory.fuzzy.FuzzyInteger(100, 99999)
    invoice_ok = True

    @factory.lazy_attribute
    def timestamp(self):
        datetime_start = fake.past_datetime(start_date="-1y")
        return fake.date_time_ad(start_datetime=datetime_start, tzinfo=pytz.UTC)

    @factory.lazy_attribute
    def amount(self):
        return self.strategy.patron.beneficiary.first().category.fee

    class Meta:
        model = Payment
        django_get_or_create = ("invoice_number",)


class QuotaFactory(DjangoModelFactory):
    payment = factory.Iterator(Payment.objects.all())

    @factory.lazy_attribute
    def member(self):
        return self.payment.strategy.patron.beneficiary.first()

    @factory.lazy_attribute_sequence
    def year(self, n):
        first_month = self.member.first_payment_month
        first_year = self.member.first_payment_year
        payed_quotas = self.member.quota_set.count()

        years_ahead = math.floor((first_month + payed_quotas - 1) / 12)

        return first_year + years_ahead

    @factory.lazy_attribute_sequence
    def month(self, n):
        first_month = self.member.first_payment_month
        payed_quotas = self.member.quota_set.count()
        months_ahead = payed_quotas % 12
        months_sum = first_month + months_ahead
        if months_sum > 12:
            return months_sum - 12
        return months_sum

    class Meta:
        model = Quota
        django_get_or_create = ("year", "month", "member")
