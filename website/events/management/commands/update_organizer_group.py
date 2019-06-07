from django.core.management.base import BaseCommand
from events.helpers.permissions import create_organizer_group


class Command(BaseCommand):
    help = 'Update base_organizer group and perms'

    def handle(self, *args, **options):
        create_organizer_group()
        self.stdout.write(self.style.SUCCESS('Successfully updated base_organizer group '))
