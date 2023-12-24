import logging
import os

from mercadopago import SDK

LIMIT = 500

logger = logging.getLogger('mercadopago')


def get_raw_mercadopago_info():
    """Get records from Mercadopago API.

    As different hits bring different "total" values indicated, we record what is the
    max of those, and only stop hitting when we get no results from one of those endpoints.
    """
    logger.debug('Connecting with mercadopago')
    auth_token = os.getenv('MERCADOPAGO_AUTH_TOKEN')
    mp = SDK(auth_token)

    filters = {'status': 'approved', 'limit': LIMIT, 'begin_date': 'NOW-3MONTHS'}
    offset = 0
    results = []
    max_total_exposed = 0
    while True:
        filters["offset"] = offset
        response = mp.payment().search(filters)
        assert response['status'] == 200

        quant_results = len(response['response']['results'])
        paging = response['response']['paging']
        max_total_exposed = max(max_total_exposed, paging["total"])
        logger.debug(
            'Getting response from mercadopago, len=%d paging=%s', quant_results, paging)

        results.extend(response['response']['results'])
        if not response['response']['results']:
            if paging["total"] == max_total_exposed:
                # didn't get any result and reported "total" is the biggest seen so far
                break
        offset += quant_results

    logger.info('Got response from mercadopago, %d items', len(results))
    return results
