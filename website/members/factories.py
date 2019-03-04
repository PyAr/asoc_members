import factory
import factory.fuzzy
from factory.django import DjangoModelFactory
from members.models import Category, Patron, Member, Organization, Person
from random import choice
from faker import Faker


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
    first_payment_month = fake.month
    first_payment_year = factory.fuzzy.FuzzyInteger(2010, 2025)

    class Meta:
        model = Member
        django_get_or_create = ("legal_id",)

    @factory.lazy_attribute
    def registration_date(self):
        date_start = fake.past_date(start_date="-365d", tzinfo=None)
        return fake.date_between_dates(date_start=date_start)


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
