import logging
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from members import logic

from . import _mp

logger = logging.getLogger('management_commands')


class Command(BaseCommand):
    help = 'Import payments from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('--payment-id', type=int, nargs='?')
        parser.add_argument('--payer-id', type=str, nargs='?')
        parser.add_argument('--custom-fee', type=int, nargs='?')

    def handle(self, *args, **options):
        payment_id = options.get('payment_id')
        payer_id = options.get('payer_id')
        if payment_id is not None or payer_id is not None:
            # if filtering, we want verbose
            logging.getLogger('').setLevel(logging.DEBUG)
        custom_fee = options.get('custom_fee')
        if custom_fee is not None:
            custom_fee = Decimal(custom_fee)

        raw_info = _mp.get_raw_mercadopago_info()
        if raw_info is None:
            return

        records = self.process_mercadopago(raw_info, payment_id, payer_id)
        logic.create_recurring_payments(records, custom_fee=custom_fee)

    def process_mercadopago(self, results, filter_payment_id, filter_payer_id):
        """Process Mercadopago info, building a per-payer sorted structure."""
        payments = []
        for info in results:

            # discard weird records about cards authorizations (payer may not be
            # there or just be empty)
            if not info.get("payer"):
                logger.debug("Discarding non-payer record: %s", info)
                continue

            payer_id = info['payer']['id']
            assert payer_id is not None
            payer_id = str(payer_id)

            # only suscriptions are handled here; examples:
            #   Cuota mensual socio adherente 2018
            #   Socies Actives cuota 2019
            #   Socies Adherentes cuota 2023
            reason = info['description']
            reason_is_subscription = reason.startswith((
                "Socies Adherentes cuota",
                "Socies Actives cuota",
                "Cuota mensual",
            ))
            if not reason_is_subscription:
                logger.debug("Discarding non-subscription record: %s", info)
                continue

            # apply filters, if given
            if filter_payment_id is not None and info['id'] != filter_payment_id:
                continue
            if filter_payer_id is not None and payer_id != filter_payer_id:
                continue

            # needed information to record the payment
            timestamp = parse_datetime(info['date_approved'])
            amount = Decimal(info['transaction_amount'])
            if amount <= 0:
                logger.debug("Discarding invalid amount: %s", info)
                continue

            # some info to identify the payer in case it's not in our DB
            id_helper = {
                'reason': reason,
                'payment_id': info['id'],
            }

            payments.append({
                'timestamp': timestamp,
                'amount': amount,
                'payer_id': payer_id,
                'id_helper': id_helper,
            })
        return payments
