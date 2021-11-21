"""
Populates database with sample data.
"""
from django.core.management.base import BaseCommand
from events.factories import ProviderFactory
from events.models import Provider


class Command(BaseCommand):
    help = "Create provider data for testing."

    def add_arguments(self, parser):
        parser.add_argument("count", type=int)

    def handle(self, *args, **options):
        providers_count = Provider.objects.count()
        q = options["count"]
        ProviderFactory.create_batch(q)
        providers_count = Provider.objects.count() - providers_count
        self.stdout.write(
            self.style.SUCCESS("Successfully created Providers instances (count %d)"
                               % providers_count)
        )
