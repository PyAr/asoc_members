"""Get all mercadopago payments that are NOT recurring."""

import csv
import logging
from decimal import Decimal

from dateutil import parser
from django.core.management.base import BaseCommand

from . import _mp

# how many records we'll retrieve from Mercadopago (aiming to be all of them)
LIMIT = 500

logger = logging.getLogger('management_commands')


class Command(BaseCommand):
    help = 'Import payments from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('year', type=str)
        parser.add_argument('month', type=str)

    def handle(self, *args, **options):
        year = int(options['year'])
        month = int(options['month'])

        raw_info = _mp.get_raw_mercadopago_info()
        if raw_info is None:
            return

        records = self.process_mercadopago(raw_info, year, month)

        filepath = "report-inusual-{}{}.csv".format(year, month)
        with open(filepath, 'wt', encoding='utf8') as fh:
            writer = csv.DictWriter(fh, fieldnames=records[0].keys())
            writer.writeheader()
            for record in records:
                writer.writerow(record)
        logger.info("Done, file %s saved ok", filepath)

    def process_mercadopago(self, results, year, month):
        """Process Mercadopago info."""
        payments = []
        for info in results:

            if info['operation_type'] == 'recurring_payment':
                continue

            date_created = parser.parse(info['date_created'])
            if date_created.year != year or date_created.month != month:
                continue

            if info['status'] != 'approved':
                # this excludes specially some "refunded" operations
                continue

            # needed information to record the payment
            payer_id = "{type} {number}".format(**info['card']['cardholder']['identification'])
            payment = {
                'id': info['id'],
                'date_approved': parser.parse(info['date_approved']),
                'amount': Decimal(info['transaction_amount']),
                'payer_name': info['card']['cardholder']['name'],
                'payer_id': payer_id,
                'reference': info['external_reference'],
                'reason': info['reason'],
            }

            assert info['operation_type'] == 'regular_payment'
            assert payer_id is not None
            payments.append(payment)

        return payments
