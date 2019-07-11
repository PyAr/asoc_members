import json
import os

from django.core.management.base import BaseCommand, CommandError

from members.models import Patron, PaymentStrategy, Payment, Person


class Command(BaseCommand):
    help = 'Import payments from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str)

    def handle(self, *args, **options):
        if options['filename'] is None:
            raise CommandError('You must specify the path of file.')

        # make sure file path resolves
        if not os.path.isfile(options['filename']):
            raise CommandError('File does not exists.')

        with open(options['filename']) as input_file:
            payments = json.load(input_file)

        template = 'Cargado automáticamente de {}\n{}'
        filename = options['filename']
        errors = []
        for payment in payments:
            msg = template.format(filename, payment['strategy']['comment'])
            patron = self.get_patron(payment)
            if patron is None:
                self.stdout.write('No Patron Found: ' + str(payment))
                errors.append(payment)
                continue
            strategy, created = PaymentStrategy.objects.get_or_create(
                patron=patron,
                platform=PaymentStrategy.MERCADO_PAGO,
                id_in_platform=payment['strategy']['id'],
                defaults={'comments': msg})
            payment_instance, created = Payment.objects.get_or_create(
                # TODO: Fix Timestamp object
                timestamp=payment['timestamp'],
                amount=payment['amount'],
                defaults={
                    'comments': template.format(
                        filename,
                        payment['comment']),
                    'strategy': strategy,
                })
        self.stdout.write(str(errors) + ' ' + str(len(errors)))

    def get_patron(self, payment):
        patron = None
        patron_query = Patron.objects.filter(email=payment['strategy']['patron']['email'])
        if patron_query.exists():
            patron = patron_query.first()
            self.stdout.write('Hecho!')
        else:
            # Patron doesn't have the Person mail.
            self.stdout.write(str(payment))
            document_number = payment['strategy']['patron']['comment'].split('DNI')[-1].strip()
            self.stdout.write(document_number)
            person_query = Person.objects.filter(document_number=document_number)
            if person_query.exists():
                person = person_query.first()
                if person.membership is not None:
                    patron = person.membership.patron
                    # TODO: What happends if the person did the payment and
                    # doesn't have membership
        return patron
