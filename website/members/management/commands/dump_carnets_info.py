import csv

from django.core.management.base import BaseCommand

from members.models import Member, Person


class Command(BaseCommand):
    help = "Generate the missing invoices"

    def handle(self, *args, **options):
        members = (
            Member.objects
            .filter(legal_id__isnull=False, shutdown_date__isnull=True)
            .order_by('legal_id')
        ).all()

        headers = ['legal_id', 'last_name', 'first_name', 'email', 'nick', 'picture']
        with open("dump-carnets.csv", 'wt', encoding='utf8') as fh:
            writer = csv.DictWriter(fh, fieldnames=headers)
            writer.writeheader()

            for member in members:
                if not isinstance(member.entity, Person):
                    continue

                person = member.person
                d = {
                    'legal_id': member.legal_id,
                    'last_name': person.last_name,
                    'first_name': person.first_name,
                    'email': person.email,
                    'nick': person.nickname,
                    'picture': person.picture,
                }
                writer.writerow(d)
