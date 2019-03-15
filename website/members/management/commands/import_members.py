import datetime
import os

from django.core.management.base import BaseCommand, CommandError

from members.models import Person, Member, Category, Patron


class Command(BaseCommand):
    help = "Import members from csv generated with data from Google Spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', default=False)
        parser.add_argument('filename', type=str)

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # make sure file path resolves
        if not os.path.isfile(options['filename']):
            raise CommandError("File does not exists.")

        cols = [
            None,
            "EMail",
            "Tipo",
            "Tipo socio",
            "Nombre",
            "Apellido",
            "DNI",
            "Nacionalidad",
            "Fecha Nacimiento",
            "Estado Civil",
            "Profesión",
            "CP",
            "Dirección",
            "Forma de pago",
            None,
            None,
            None,
            None,
            None,
            None,
            "Pais",
            "Provincia",
            "Ciudad",
        ]

        with open(options["filename"]) as fh:
            for line in fh:
                row = {}
                for col, datum in zip(cols, line.split('\t')):
                    if col is not None:
                        row[col] = datum.strip()
                row['Fecha Nacimiento'] = datetime.datetime.strptime(
                    row['Fecha Nacimiento'], "%m/%d/%Y")  # English!!
                member = self.create(row, dry_run)
                if not dry_run:
                    self.stdout.write("Member imported: {}".format(member))

    def create(self, row, dry_run):
        if row["Tipo"] != "Humano":
            raise ValueError("Not human! " + str(row))

        print("Importing:", row)
        member_type = row['Tipo socio'].split()[-1]
        category = Category.objects.get(name=member_type)

        first_name = row['Nombre']
        last_name = row['Apellido']
        email = row['EMail']
        patron = Patron(
            name="{} {}".format(first_name, last_name),
            email=email,
            comments='Automatically loaded with modified import-from-text script',
        )
        if not dry_run:
            patron.save()

        member = Member(
            category=category,
            patron=patron)
        if not dry_run:
            member.save()

        person = Person(
            first_name=first_name,
            last_name=last_name,
            email=email,
            document_number=row['DNI'],
            # nickname=row['Nick'].strip(),
            nationality=row['Nacionalidad'],
            marital_status=row['Estado Civil'],
            occupation=row['Profesión'],
            birth_date=row['Fecha Nacimiento'],
            street_address=row['Dirección'],
            city=row['Ciudad'],
            zip_code=row['CP'],
            province=row['Provincia'],
            country=row['Pais'],
            membership=member,
            comments='Automatically loaded with modified import-from-text script',
        )
        if not dry_run:
            person.save()

        return member
