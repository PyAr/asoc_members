import csv
import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from members.models import Person, Member, Category, Patron


CAT_ESTUDIANTE = 'Estudiante'


class Command(BaseCommand):
    help = "Import members from csv generated with data from Google Spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str)

    def handle(self, *args, **options):
        if options['filename'] is None:
            raise CommandError("You must specify the path of file.")

        # make sure file path resolves
        if not os.path.isfile(options['filename']):
            raise CommandError("File does not exists.")

        dataReader = csv.reader(open(options["filename"]), delimiter=',', quotechar='"')
        for member_value in dataReader:
            person, patron = self.get_or_create_person_and_patron(member_value)
            category = self.get_or_create_category(member_value)
            person.membership, created = Member.objects.update_or_create(
                legal_id=member_value[0].strip(),
                defaults={
                    'registration_date': datetime.strptime(member_value[1].strip(), "%d/%m/%Y"),
                    'category': category,
                    'patron': patron,
                    'has_student_certificate': True if category.name == CAT_ESTUDIANTE else False,
                    'has_subscription_letter': True
                })
            person.save()
            self.stdout.write("Member imported: {}".format(person.membership))

    def get_or_create_category(self, values):
        category, created = Category.objects.get_or_create(
            name=values[5].strip(),
            defaults={
                'description': values[5].strip(),
                'fee': 0
            })
        return category

    def get_or_create_person_and_patron(self, values):
        person, created = Person.objects.update_or_create(
            first_name=values[3].strip(),
            last_name=values[4].strip(),
            email=values[7].strip(),
            defaults={
                'document_number': values[6].strip(),
                'nickname': values[8].strip(),
                'nationality': values[10].strip(),
                'marital_status': values[11].strip(),
                'occupation': values[12].strip(),
                'birth_date': datetime.strptime(values[13].strip(), "%d/%M/%Y"),
                'street_address': values[14].strip()
            })

        patron, created = Patron.objects.update_or_create(
            name=person.full_name,
            email=person.email,
            defaults={
                'comments': 'Automatically loaded with PyCAmp 2018 script',
            })

        return person, patron
