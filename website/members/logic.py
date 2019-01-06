import logging
from operator import itemgetter

from members.models import Quota, Payment, PaymentStrategy, Member

logger = logging.getLogger(__name__)


def _increment_year_month(year, month):
    """Add one month to the received year/month."""
    month += 1
    if month == 13:
        year += 1
        month = 1
    return year, month


def _get_year_month_range(year, month, quantity):
    """Return several year/month pairs from a given start."""
    yield year, month
    for _ in range(quantity - 1):
        year, month = _increment_year_month(year, month)
        yield year, month


def create_payment(member, timestamp, amount, payment_strategy, first_unpaid=None):
    """Create a payment from the given strategy to the specific member."""
    # get the latest unpaid monthly fee
    if first_unpaid is None:
        try:
            last_quota = Quota.objects.filter(member=member).latest()
        except Quota.DoesNotExist:
            first_unpaid = (member.first_payment_year, member.first_payment_month)
        else:
            first_unpaid = _increment_year_month(last_quota.year, last_quota.month)
    first_unpaid_year, first_unpaid_month = first_unpaid

    # calculate how many fees covers the amount, supporting not being exact but for a very
    # small difference
    paying_quant_real = amount / member.category.fee
    paying_quant_int = int(round(paying_quant_real))
    if abs(paying_quant_real - paying_quant_int) > paying_quant_int * 0.01:
        raise ValueError(
            "Paying amount too inexact! amount={} fee={}".format(amount, member.category.fee))

    # create the payment itself
    payment = Payment.objects.create(timestamp=timestamp, amount=amount, strategy=payment_strategy)

    # create the monthly fee(s)
    yearmonths = _get_year_month_range(first_unpaid_year, first_unpaid_month, paying_quant_int)
    for year, month in yearmonths:
        Quota.objects.create(payment=payment, month=month, year=year, member=member)


def create_recurring_payments(recurring_records):
        # group payments per payer and order them
        grouped = {}
        for record in recurring_records:
            grouped.setdefault(record['payer_id'], []).append(record)
        for records in grouped.values():
            records.sort(key=itemgetter('timestamp'))

        count_without_new_payments = 0
        for payer, retrieved_payments in grouped.items():
            # get strategy for the payer
            try:
                strategy = PaymentStrategy.objects.get(
                    platform=PaymentStrategy.MERCADO_PAGO, id_in_platform=payer)
            except PaymentStrategy.DoesNotExist:
                payment = retrieved_payments[0]
                logger.error("PaymentStrategy not found for payer %r: %s", payer, payment)
                continue

            # get latest payment done with this strategy
            last_payment_recorded = Payment.objects.filter(strategy=strategy).last()

            if last_payment_recorded is None:
                # no payments found, need to record all the retrieved payments
                remaining_payments = retrieved_payments
            else:
                # detect which is last one recorded
                for pos, retrieved_payment in enumerate(retrieved_payments):
                    if retrieved_payment['timestamp'] == last_payment_recorded.timestamp:
                        # found! need to record the remaining ones
                        remaining_payments = retrieved_payments[pos + 1:]
                        break
                else:
                    # no payment match found!
                    logger.error(
                        "Payment not found to match %s: %s",
                        last_payment_recorded, retrieved_payments)
                    continue

            # get the member from the patron
            try:
                member = Member.objects.get(patron=strategy.patron)
            except Member.MultipleObjectsReturned:
                # for recurring payments we still do not support having
                # more than one member for the given patron
                logger.error("Found more than one member for Patron: %s", strategy.patron)
                continue

            if remaining_payments:
                logger.info(
                    "Creating recurring payments from payer=%s to member=%s: %s",
                    payer, member, remaining_payments)
            else:
                count_without_new_payments += 1
            for payment_info in remaining_payments:
                create_payment(member, payment_info['timestamp'], payment_info['amount'], strategy)

        logger.info("Processes %d payers without new payments", count_without_new_payments)


def get_debt_state(member, limit_year, limit_month):
    """Return if the member is in debt, and the missing quotas.

    The quotas verified are from first payment up to the given year/month limit (including).
    """
    # verify the limit is after member started paying
    if member.first_payment_year == limit_year:
        if member.first_payment_month > limit_month:
            return []
    elif member.first_payment_year > limit_year:
        return []

    # build a set for the year/month of paid quotas
    quotas = Quota.objects.filter(member=member).all()
    yearmonths_paid = {(q.year, q.month) for q in quotas}

    # build a set of all the year/month the member should have paid up to (including) the limit
    year_to_check = member.first_payment_year
    month_to_check = member.first_payment_month
    should_have_paid = set()
    while True:
        should_have_paid.add((year_to_check, month_to_check))
        year_to_check, month_to_check = _increment_year_month(year_to_check, month_to_check)
        if year_to_check == limit_year:
            if month_to_check > limit_month:
                break
        elif year_to_check > limit_year:
            break

    return sorted(should_have_paid - yearmonths_paid)
