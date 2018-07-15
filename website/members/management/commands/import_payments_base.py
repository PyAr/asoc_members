import csv
import datetime
import decimal
import os

from django.core.management.base import BaseCommand, CommandError

from members import logic
from members.models import Person, Member, PaymentStrategy

PLATFORMS = {
    'todopago': PaymentStrategy.TODO_PAGO,
    'transfer': PaymentStrategy.TRANSFER,
}

MSG_BOOTSTRAP = "Loaded automatically at system bootstrap"


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
                self.process(row)

    def get_member_set_first_payments(self, row):
        """Return the Member, identifying it from legal id or dni."""
        legal_id = row['Legal Id'].strip()
        if legal_id:
            member = Member.objects.get(legal_id=int(legal_id))
        else:
            dni = row['DNI'].strip()
            person = Person.objects.get(document_number=dni)
            member = person.membership

        # set first payments
        p_init = row['Pago init'].strip()
        pi_month, pi_year = map(int, p_init.split('-'))
        member.first_payment_month = pi_month
        member.first_payment_year = pi_year
        member.save()

        return member

    def create_manual(self, row):
        member = self.get_member_set_first_payments(row)
        assert member.category.name == row['Tipo socio']

        paypairs = []
        for i in range(1, 5):
            tstamp = row['timestamp' + str(i)].strip()
            amount = row['amount' + str(i)].strip()
            if tstamp:
                assert amount
                paypairs.append((tstamp, decimal.Decimal(amount)))

        platform = PLATFORMS[row['platform']]
        strategy = PaymentStrategy.objects.create(
            platform=platform, id_in_platform='', patron=member.patron, comments=MSG_BOOTSTRAP)

        for tstamp, amount in paypairs:
            tstamp = datetime.datetime.strptime(tstamp, "%d/%M/%y")
            logic.create_payment(member, tstamp, amount, strategy)

    def create_mercadopago(self, row):
        id_in_platform = row['plat_id'].strip()
        assert id_in_platform

        member = self.get_member_set_first_payments(row)
        assert member.category.name == row['Tipo socio']

        PaymentStrategy.objects.create(
            platform=PaymentStrategy.MERCADO_PAGO, id_in_platform=id_in_platform,
            patron=member.patron, comments="Loaded automatically at system bootstrap")

    def process(self, row):
        self.stdout.write("Processing: {} {}".format(row['Nombre'], row['Apellido']))
        if row['platform'] in ('transfer', 'todopago'):
            self.create_manual(row)
        elif row['platform'] == 'mercadopago':
            self.create_mercadopago(row)
        elif row['platform'] == '-':
            assert row['Tipo socio'] in ('Cadete', 'Colaborador')
        else:
            raise ValueError("Bad platform: {!r}".format(row['platform']))
