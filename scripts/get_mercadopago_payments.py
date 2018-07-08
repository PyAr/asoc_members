#!/usr/bin/env fades

import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv  # fades python-dotenv
from mercadopago import MP  # fades

# how many records we'll retrieve from Mercadopago (aiming to be all of them)
LIMIT = 500

load_dotenv()

logger = logging.getLogger(__name__)


def get_payments_from_mercadopago(filters, output=None):
    """Connect to mercadopago and retrieves all payments with applied filters."""

    MERCADOPAGO_CLIENT_ID = os.getenv('MERCADOPAGO_CLIENT_ID')
    MERCADOPAGO_CLIENT_SECRET = os.getenv('MERCADOPAGO_CLIENT_SECRET')

    mp = MP(MERCADOPAGO_CLIENT_ID, MERCADOPAGO_CLIENT_SECRET)
    logger.debug('Connecting with mercadopago')

    response = mp.search_payment(filters, limit=LIMIT, offset=0)
    assert response['response']['paging']['total'] <= LIMIT
    logger.info('Getting response from mercadopago, paging %s', response['response']['paging'])

    if output is None:
        output = 'mercadopago_{}.json'.format(datetime.utcnow().isoformat())

    with open(output, 'wt', encoding='utf8') as output_file:
        json.dump(response, output_file)
    logger.info('Saved file -> %s', output)

    return output


def _process_mercadopago_file(filename):
    """Open mercadopago JSON file and return a valid payments list."""

    logger.info('Opening file <- %s', filename)
    with open(filename, 'r') as input_file:
        payment_data = input_file.read()
        response = json.loads(payment_data)

    payments = []
    values = response['response']['results']
    for item in values:
        patron = '{} {}'.format(
            item['collection']['cardholder']['identification']['type'],
            item['collection']['cardholder']['identification']['number'])
        payment = {
            'timestamp': item['collection']['date_approved'],
            'amount': item['collection']['total_paid_amount'],
            'strategy': {
                'id': item['collection']['payer']['id'],
                'comment': item['collection']['operation_type'],
                'patron': {
                    'name': item['collection']['cardholder']['name'],
                    'email': item['collection']['payer']['email'],
                    'comment': patron,
                },
            },
            'comment': item['collection']['reason'],
        }
        payments.append(payment)
        payment_id = item['collection']['id']
        logger.debug('Payment %s processed from file', payment_id)
    return payments


def _write_payments_file_from_list(payments, output=None):
    """ From payments list write payments file. """

    if output is None:
        output = 'payments_{}.json'.format(datetime.utcnow().isoformat())

    with open(output, 'w') as output_file:
        json.dump(payments, output_file)
    logger.info('Saved file -> %s', output)

    return output


def process_file_for_import(filename, output=None):
    payments = _process_mercadopago_file(filename)
    output = _write_payments_file_from_list(payments)
    return output


if __name__ == '__main__':
    import sys

    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(funcName)30s - %(levelname)9s - %(message)s'
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    filters = {
        'status': 'approved',
    }
    payments_file = get_payments_from_mercadopago(filters)
    payments = process_file_for_import(payments_file)
