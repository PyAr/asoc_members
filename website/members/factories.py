import factory
import factory.fuzzy
from factory.django import DjangoModelFactory
from members.models import Category, Patron, Member, Organization, Person
from random import choice
from faker import Faker


fake = Faker("es_MX")


class CategoryFactory(DjangoModelFactory):
    name = factory.LazyAttribute(lambda x: choice(Category.CATEGORY_CHOICES)[0])
    description = factory.fuzzy.FuzzyText(length=50)
    fee = factory.fuzzy.FuzzyDecimal(0, 50000, 2)

    class Meta:
        model = Category
        django_get_or_create = ("name",)


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
    # category = factory.Iterator(Category.objects.all())
    patron = factory.SubFactory(PatronFactory)
    category = factory.SubFactory(CategoryFactory)

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
    document_number = factory.fuzzy.FuzzyInteger(90000000, 99999999)
    email = fake.email
    street_address = fake.street_address

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
