import csv
import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from members.models import Person, Patron


class Command(BaseCommand):
    help = "Import people from csv generated with data from Google Spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str)

    def handle(self, *args, **options):
        if options['filename'] is None:
            raise CommandError("You must specify the path of file.")

        # make sure file path resolves
        if not os.path.isfile(options['filename']):
            raise CommandError("File does not exists.")

        with open(options["filename"]) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                person = self.get_or_create_person_and_patron(row)
                self.stdout.write("Person imported: {}".format(person))

    def get_or_create_person_and_patron(self, values):
        person, created = Person.objects.update_or_create(
            first_name=values['Nombre'].strip(),
            last_name=values['Apellido'].strip(),
            email=values['EMail'].strip(),
            defaults={
                'document_number': values['DNI'].strip(),
                'nickname': values['Nick'].strip(),
                'nationality': values['Nacionalidad'].strip(),
                'marital_status': values['Estado Civil'].strip(),
                'occupation': values['Profesión'].strip(),
                'birth_date': datetime.strptime(values['Fecha Nacimiento'].strip(), "%d/%m/%Y"),
                'street_address': values['Domicilio'].strip(),
                'comments': "Tipo de socio elegido: %s" % values["Tipo socio"].strip()
            })

        Patron.objects.update_or_create(
            name=person.full_name,
            email=person.email,
            defaults={
                'comments': 'Automatically loaded with PyCAmp 2018 script',
            })

        return person
