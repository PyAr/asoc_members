import datetime
import csv
import os
import re

from django.core.management.base import BaseCommand, CommandError

from members.models import Person, Patron, Category, Member

MONTHS = {
    'ene.': 1,
    'feb.': 2,
    'mar.': 3,
    'abr.': 4,
    'may.': 5,
    'jun.': 6,
    'jul.': 7,
    'ago.': 8,
    'sep.': 9,
    'oct.': 10,
    'nov.': 11,
    'dic.': 12,
}


def get_date(date_string):
    """Transform the date from spreadsheet to a datetime object.

    The source format is quite weird, but the only option to not get confused about
    language-dependant ordering, e.g.:

        25-abr.-2018
        1-jul.-2016
    """
    day, monthname, year = date_string.split("-")
    return datetime.date(year=int(year), month=MONTHS[monthname], day=int(day))


def split_address(complete):
    """Split one line of address in its components."""
    if complete.count(",") == 2:
        streetadd, city_pc, prov = [x.strip() for x in complete.split(",")]
        country = "Argentina"
    elif complete.count(",") == 3:
        streetadd, city_pc, prov, country = [x.strip() for x in complete.split(",")]
    else:
        streetadd, city_pc, prov, country = ("", "", "", "")

    m = re.match(r"(.*) \((.*)\)", city_pc)
    if m:
        city, postcode = m.groups()
    else:
        city, postcode = ("", "")

    if "" in (complete, streetadd, city, prov, country):
        print("======== address", (complete, streetadd, city, postcode, prov, country))
    return streetadd, city, postcode, prov, country


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
                member = self.create(row)
                self.stdout.write("Member imported: {}".format(member))

    def create(self, row):
        first_name = row['Nombre'].strip()
        last_name = row['Apellido'].strip()
        email = row['EMail'].strip()
        patron = Patron(
            name="{} {}".format(first_name, last_name),
            email=email,
            comments='Automatically loaded with PyCamp 2018 script',
        )
        patron.save()

        category = Category.objects.get(name=row["Tipo socio"].strip())
        member = Member(
            category=category,
            patron=patron,
            has_student_certificate=row['C.Estud'].strip() == "✓",
            has_subscription_letter=row['Firmó'].strip() == "✓"
        )
        member.save()

        street_address, city, zip_code, province, country = split_address(row['Domicilio'].strip())
        person = Person(
            first_name=first_name,
            last_name=last_name,
            email=email,
            document_number=row['DNI'].strip(),
            nickname=row['Nick'].strip(),
            nationality=row['Nacionalidad'].strip(),
            marital_status=row['Estado Civil'].strip(),
            occupation=row['Profesión'].strip(),
            birth_date=get_date(row['Fecha Nacimiento'].strip()),
            street_address=street_address,
            city=city,
            zip_code=zip_code,
            province=province,
            country=country,
            membership=member,
            comments='Automatically loaded with PyCamp 2018 script',
        )
        person.save()

        return member
