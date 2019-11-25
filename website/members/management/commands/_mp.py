import logging
import os

from mercadopago import MP

LIMIT = 500

logger = logging.getLogger('mercadopago')


def get_raw_mercadopago_info():
    """Get records from Mercadopago API."""
    mercadopago_client_id = os.getenv('MERCADOPAGO_CLIENT_ID')
    mercadopago_client_secret = os.getenv('MERCADOPAGO_CLIENT_SECRET')

    mp = MP(mercadopago_client_id, mercadopago_client_secret)
    logger.debug('Connecting with mercadopago')

    filters = {'status': 'approved'}
    offset = 0
    results = []
    while True:
        response = mp.search_payment(filters, limit=LIMIT, offset=offset)
        assert response['status'] == 200
        logger.debug(
            'Getting response from mercadopago, paging %s', response['response']['paging'])
        results.extend(response['response']['results'])
        if len(response['response']['results']) < LIMIT:
            break
        offset += LIMIT

    logger.info('Got response from mercadopago, %d items', len(results))
    return results
