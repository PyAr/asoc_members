import logging
import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from mercadopago import MP

from members import logic

# how many records we'll retrieve from Mercadopago (aiming to be all of them)
LIMIT = 500

logger = logging.getLogger('management_commands')


class Command(BaseCommand):
    help = 'Import payments from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('--payment_id', type=int, nargs='?')
        parser.add_argument('--payer_id', type=str, nargs='?')

    def handle(self, *args, **options):
        payment_id = options.get('payment_id')
        payer_id = options.get('payer_id')
        if payment_id is not None or payer_id is not None:
            # if filtering, we want verbose
            logging.getLogger('').setLevel(logging.DEBUG)

        raw_info = self.get_raw_mercadopago_info()
        if raw_info is None:
            return

        records = self.process_mercadopago(raw_info, payment_id, payer_id)
        logic.create_recurring_payments(records)

    def get_raw_mercadopago_info(self):
        """Get records from Mercadopago API."""
        mercadopago_client_id = os.getenv('MERCADOPAGO_CLIENT_ID')
        mercadopago_client_secret = os.getenv('MERCADOPAGO_CLIENT_SECRET')

        mp = MP(mercadopago_client_id, mercadopago_client_secret)
        logger.debug('Connecting with mercadopago')

        filters = {'status': 'approved'}
        response = mp.search_payment(filters, limit=LIMIT, offset=0)
        if response['response']['paging']['total'] >= LIMIT:
            logger.error("Hit the limit of Mercadopago transactions retrieval")
            return
        logger.info('Getting response from mercadopago, paging %s', response['response']['paging'])
        return response

    def process_mercadopago(self, mercadopago_response, filter_payment_id, filter_payer_id):
        """Process Mercadopago info, building a per-payer sorted structure."""
        payments = []
        for item in mercadopago_response['response']['results']:
            info = item['collection']

            # needed information to record the payment
            timestamp = parse_datetime(info['date_approved'])
            amount = Decimal(info['total_paid_amount'])
            payer_id = info['payer']['id']
            assert payer_id is not None
            payer_id = str(payer_id)

            # apply filters, if given
            if filter_payment_id is not None and info['id'] != filter_payment_id:
                continue
            if filter_payer_id is not None and payer_id != filter_payer_id:
                continue

            # some info to identify the payer in case it's not in our DB
            id_helper = {
                'cardholder': info['cardholder'],
                'reason': info['reason'],
                'payment_id': info['id'],
            }

            payments.append({
                'timestamp': timestamp,
                'amount': amount,
                'payer_id': payer_id,
                'id_helper': id_helper,
            })
        return payments
