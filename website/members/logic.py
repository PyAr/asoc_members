import logging
from operator import itemgetter

from members.models import Quota, Payment, PaymentStrategy, Member

logger = logging.getLogger(__name__)


def increment_year_month(year, month):
    """Add one month to the received year/month."""
    month += 1
    if month == 13:
        year += 1
        month = 1
    return year, month


def decrement_year_month(year, month):
    """Subtract one month to the received year/month."""
    month -= 1
    if month <= 0:
        year -= 1
        month = 12
    return year, month


def get_year_month_range(year, month, quantity):
    """Return several year/month pairs from a given start."""
    yield year, month
    for _ in range(quantity - 1):
        year, month = increment_year_month(year, month)
        yield year, month


def create_payment(
        member, timestamp, amount, payment_strategy, first_unpaid=None,
        comments='', custom_fee=None):
    """Create a payment from the given strategy to the specific member."""
    logger.info("Creating payment! member=%s amount=%r custom_fee=%r", member, amount, custom_fee)
    # get the latest unpaid monthly fee
    if first_unpaid is None:
        try:
            last_quota = Quota.objects.filter(member=member).latest()
        except Quota.DoesNotExist:
            first_unpaid = (member.first_payment_year, member.first_payment_month)
        else:
            first_unpaid = increment_year_month(last_quota.year, last_quota.month)
    first_unpaid_year, first_unpaid_month = first_unpaid

    # calculate how many fees covers the amount, supporting not being exact but for a very
    # small difference
    fee = member.category.fee if custom_fee is None else custom_fee
    paying_quant_real = amount / fee
    paying_quant_int = int(round(paying_quant_real))
    if abs(paying_quant_real - paying_quant_int) > paying_quant_int * 0.01:
        raise ValueError("Paying amount too inexact! amount={} fee={}".format(amount, fee))

    # create the payment itself
    payment = Payment.objects.create(
        timestamp=timestamp, amount=amount, strategy=payment_strategy, comments=comments)

    # create the monthly fee(s)
    yearmonths = get_year_month_range(first_unpaid_year, first_unpaid_month, paying_quant_int)
    for year, month in yearmonths:
        Quota.objects.create(payment=payment, month=month, year=year, member=member)


def create_recurring_payments(recurring_records, custom_fee=None):
    """Create payments and quotas from external recurring payments."""
    # group payments per payer and order them, avoiding duplicated payments
    grouped = {}
    for record in recurring_records:
        payer_records = grouped.setdefault(record['payer_id'], [])
        # inefficient to walk on all the items everytime, but these are really short lists
        this_payment_id = record['id_helper']['payment_id']
        if any(this_payment_id == r['id_helper']['payment_id'] for r in payer_records):
            # duplicated! ignoring
            continue
        payer_records.append(record)
    for records in grouped.values():
        records.sort(key=itemgetter('timestamp'))

    count_without_new_payments = 0
    for payer, retrieved_payments in grouped.items():
        logger.debug("Processing payments for payer %r: %d", payer, len(retrieved_payments))

        # get strategy for the payer
        try:
            strategy = PaymentStrategy.objects.get(
                platform=PaymentStrategy.MERCADO_PAGO, id_in_platform=payer)
        except PaymentStrategy.DoesNotExist:
            payment = retrieved_payments[0]
            logger.error(
                "PaymentStrategy not found for payer %r: %s (%d payments)",
                payer, payment, len(retrieved_payments))
            continue

        # get latest payment done with this strategy
        last_payment_recorded = Payment.objects.filter(strategy=strategy).last()
        logger.debug("Last payment recorded: %s", last_payment_recorded)

        if last_payment_recorded is None:
            # no payments found, need to record all the retrieved payments
            remaining_payments = retrieved_payments
        else:
            # detect which is last one recorded
            for pos, retrieved_payment in enumerate(retrieved_payments):
                logger.debug("Comparing retrieved: %d: %s", pos, retrieved_payment)
                if retrieved_payment['timestamp'] == last_payment_recorded.timestamp:
                    # found! need to record the remaining ones
                    remaining_payments = retrieved_payments[pos + 1:]
                    logger.debug(
                        "Found payment limit (remaining: %d)", len(remaining_payments))
                    break
                if retrieved_payment['timestamp'] > last_payment_recorded.timestamp:
                    # found a newer one without finding first the exact one! this is Mercadago
                    # returning bullshit
                    remaining_payments = retrieved_payments[pos:]
                    logger.warning(
                        "Found exceeding payment limit! last recorded: %s (remaining: %d)",
                        last_payment_recorded, len(remaining_payments))
                    break
            else:
                # no payment match found! all informed are old (it's just Mercadopago
                # failing) otherwise it would have been logged with warning above
                logger.debug(
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
            # use current category fee as custom fee (unless the user forced other one) to
            # ensure always *1* quota is recorded; however verify that current amount is
            # the same as the member's category fee and show a warning if needed
            this_custom_fee = custom_fee
            if this_custom_fee is None:
                this_custom_fee = payment_info['amount']
                if this_custom_fee != member.category.fee:
                    logger.warning(
                        "Payment with strange amount for member %s: %s", member, payment_info)
            create_payment(
                member, payment_info['timestamp'], payment_info['amount'],
                strategy, custom_fee=this_custom_fee)

    logger.info("Processed %d payers without new payments", count_without_new_payments)


def get_debt_state(member, limit_year, limit_month):
    """Return if the member is in debt, and the missing quotas.

    If the member has a first payment, the quotas verified are from that first payment up
    to the given year/month limit (including).

    If the member never paid, the registration date is used, and that month is also included.
    """
    if member.first_payment_year is None:
        # never paid! using registration date to start with
        yearmonths_paid = set()
        year_to_check = member.registration_date.year
        month_to_check = member.registration_date.month
    else:
        # build a set for the year/month of paid quotas
        quotas = Quota.objects.filter(member=member).all()
        yearmonths_paid = {(q.year, q.month) for q in quotas}

        year_to_check = member.first_payment_year
        month_to_check = member.first_payment_month

    # verify the limit is after member started paying
    if year_to_check == limit_year:
        if month_to_check > limit_month:
            return []
    elif year_to_check > limit_year:
        return []

    # build a set of all the year/month the member should have paid up to (including) the limit
    should_have_paid = set()
    while True:
        should_have_paid.add((year_to_check, month_to_check))
        year_to_check, month_to_check = increment_year_month(year_to_check, month_to_check)
        if year_to_check == limit_year:
            if month_to_check > limit_month:
                break
        elif year_to_check > limit_year:
            break

    return sorted(should_have_paid - yearmonths_paid)
