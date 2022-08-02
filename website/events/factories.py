from random import choice

import factory
import factory.fuzzy
from factory.django import DjangoModelFactory
from faker import Faker

from events.models import (
    Provider
)

fake = Faker("es_MX")


class ProviderFactory(DjangoModelFactory):
    document_number = factory.fuzzy.FuzzyInteger(1, 99999999)
    bank_entity = fake.company
    account_number = factory.fuzzy.FuzzyInteger(1, 9999999999999)
    account_type = factory.LazyAttribute(lambda x: choice(Provider.ACCOUNT_TYPE_CHOICES)[0])
    organization_name = fake.company
    cbu = fake.bban

    class Meta:
        model = Provider
        django_get_or_create = (
            "document_number",
        )
