"""
Populates database with sample data.
"""
from django.core.management.base import BaseCommand
from django.core import management
from django.core.management.commands import loaddata
from members.factories import (PersonFactory, OrganizationFactory, PaymentFactory,
                               PaymentStrategyFactory, QuotaFactory)
from members.models import Person, Organization, Payment, PaymentStrategy, Quota


class Command(BaseCommand):
    help = "Create sample data for testing."

    def add_arguments(self, parser):
        parser.add_argument("count", type=int)

    def handle(self, *args, **options):
        management.call_command(loaddata.Command(), "categories", verbosity=0)
        person_count = Person.objects.count()
        organization_count = Organization.objects.count()
        payment_count = Payment.objects.count()
        payment_strategy_count = PaymentStrategy.objects.count()
        quota_count = Quota.objects.count()

        q = options["count"]

        people = PersonFactory.create_batch(q)
        orgs = OrganizationFactory.create_batch(q)
        for person in people:
            strategy = PaymentStrategyFactory(patron=person.membership.patron)
            payment = PaymentFactory.create_batch(q, strategy=strategy)
            for p in payment:
                QuotaFactory(payment=p)
        for org in orgs:
            strategy = PaymentStrategyFactory(patron=org.membership.patron)
            payment = PaymentFactory.create_batch(q, strategy=strategy)
            for p in payment:
                QuotaFactory(payment=p)

        person_count = Person.objects.count() - person_count
        organization_count = Organization.objects.count() - organization_count
        payment_count = Payment.objects.count() - payment_count
        payment_strat_count = PaymentStrategy.objects.count() - payment_strategy_count
        quota_count = Quota.objects.count() - quota_count

        self.stdout.write(
            self.style.SUCCESS("Successfully created Person instances (count %d)" % person_count)
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully created Organization  instances (count %s)" % organization_count
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully created PaymentStrategy instances (count %d)" % payment_strat_count
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully created Payment instances (count %d)" % payment_count
            )
        )
        self.stdout.write(
            self.style.SUCCESS("Successfully created Quota instances (count %d)" % quota_count)
        )
