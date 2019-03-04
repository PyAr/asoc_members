from django.core.management.base import BaseCommand
from django.core import management
from django.core.management.commands import loaddata
from members.factories import PersonFactory, OrganizationFactory
from members.models import Person, Organization


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        parser.add_argument("count", type=int)

    def handle(self, *args, **options):
        management.call_command(loaddata.Command(), "category", verbosity=0)
        person_count = Person.objects.count()
        organization_count = Organization.objects.count()

        for i in range(options["count"]):
            PersonFactory()
            OrganizationFactory()

        person_count = Person.objects.count() - person_count
        organization_count = Organization.objects.count() - organization_count

        self.stdout.write(
            self.style.SUCCESS("Successfully Person create count %d" % person_count)
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully Organization create count %s" % organization_count
            )
        )
