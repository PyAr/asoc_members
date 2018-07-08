import csv
import datetime
import os
import re

from django.core.management.base import BaseCommand, CommandError

from members.models import Person, Member, Category, Patron


CAT_ESTUDIANTE = 'Estudiante'
CAT_DESCRIPTIONS = {
    'Activo': "Personas que manifiesten su adhesión con los objetivos de esta entidad, realicen activamente contribuciones al lenguaje de programación Python o a eventos y/ o proyectos relacionados, y ofrezcan su colaboración en la realización de las distintas tareas que la misma requiera. Pagarán cuota social y otras contribuciones extraordinarias que se establezcan. Participarán con voz y voto en las asambleas y podrán ser elegidos para integrar los órganos sociales, cuando tengan una antigüedad de un año (1); podrán ser designados para integrar las subcomisiones que se creen y/o presentar por escrito a la Comisión Directiva ideas y proyectos de utilidad que encuadren dentro de los fines de la Asociación.",  # NOQA
    CAT_ESTUDIANTE: "Personas físicas mayores de 18 años, que puedan demostrar, con una periodicidad anual, su condición de alumno regular en una institución de enseñanza reconocida por el Ministerio de Educación de la Nación o su equivalente, y tengan su solicitud de ingreso aprobada por la Comisión Directiva. Abonarán cuota social y no tendrán derecho a voz ni voto, ni podrán ser elegidos para integrar los órganos sociales. Aquellos estudiantes que reciban becas de estudio o premios al mérito académico relacionados con el objeto de la asociación, podrán quedar exceptuados del pago de la cuota social según lo evalúe la Comisión Directiva.",  # NOQA
    'Adherente': "Personas individuales mayores de 18 años que soliciten ingreso a la Asociación en virtud de su interés en apoyar sus objetivos y/o participar en las actividades de la misma, y fueren aceptados por la Comisión Directiva pero no reúnan las cualidades para ser socio activo u opten por pertenecer a esta categoría, pagará cuota social y tendrá derecho a voz, pero no a voto, ni podrán ser elegidos para integrar los órganos sociales.",  # NOQA
    'Cadete': "Menores de 18 años de edad; deberán acompañar su solicitud de ingreso con la autorización de sus padres o representantes legales, abonarán cuota social, no tendrán voz ni voto en las asambleas, pasando automáticamente a la categoría de socio activo, estudiante o adherente según correspondiera, al momento de alcanzar la mayoría de edad.  Aquellos aspirantes a la categoría cadete que se destaquen notoriamente en su desempeño relacionado al objeto de la asociación, podrán ser exceptuados del pago de la cuota social según lo evalúe la Comisión Directiva.",  # NOQA
    'Colaborador': "Personas que en atención a los servicios prestados a la asociación o a determinadas condiciones personales, sean designados por la Comisión Directiva y se desempeñen como colaboradores activos de al menos un proyecto o actividad de la Asociación, siendo ratificados por el 20% de los asociados con derecho a voto. Podrán ser designados para integrar las subcomisiones que se creen. Tendrán voz pero no voto en las asambleas, y no podrán ser elegidos para integrar los órganos sociales. Los socios colaboradores estarán exceptuados de abonar la cuota social, y deberán ratificar anualmente su permanencia en esta categoría mediante una solicitud que deberá ser considerada y aprobada por la Comisión Directiva. Los asociados colaboradores que deseen tener los mismos derechos que los activos deberán solicitar su admisión en dicha categoría, a cuyo efecto se ajustarán las condiciones que el presente estatuto exige para la misma.",  # NOQA
}
CAT_FEES = {
    'Activo': 200,
    CAT_ESTUDIANTE: 25,
    'Adherente': 75,
    'Cadete': 0,
    'Colaborador': 0,
}
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

    m = re.match("(.*) \((.*)\)", city_pc)
    if m:
        city, postcode = m.groups()
    else:
        city, postcode = ("", "")

    if "" in (complete, streetadd, city, prov, country):
        print("======== address", (complete, streetadd, city, postcode, prov, country))
    return streetadd, city, postcode, prov, country


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

        with open(options["filename"]) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                member = self.create(row)
                self.stdout.write("Member imported: {}".format(member))

    def create(self, row):
        category = self.get_or_create_category(row)

        first_name = row['Nombre'].strip()
        last_name = row['Apellido'].strip()
        email = row['EMail'].strip()
        patron = Patron(
            name="{} {}".format(first_name, last_name),
            email=email,
            comments='Automatically loaded with PyCamp 2018 script',
        )
        patron.save()

        member = Member(
            legal_id=int(row['Nro'].strip()),
            registration_date=get_date(row['Fecha alta'].strip()),
            category=category,
            patron=patron,
            has_student_certificate=category.name == CAT_ESTUDIANTE,
            has_subscription_letter=True,
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

    def get_or_create_category(self, values):
        name = values['Tipo socio'].strip()
        description = CAT_DESCRIPTIONS[name]
        fee = CAT_FEES[name]
        category, created = Category.objects.get_or_create(
            name=name,
            defaults={
                'description': description,
                'fee': fee,
            })
        return category
