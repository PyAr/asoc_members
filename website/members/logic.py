from members.models import Quota, Payment


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


def create_payment(member, timestamp, amount, payment_strategy):
    """Create a payment from the given strategy to the specific member."""
    # get the latest unpaid monthly fee
    try:
        last_quota = Quota.objects.filter(member=member).latest()
    except Quota.DoesNotExist:
        first_unpaid_year = member.first_payment_year
        first_unpaid_month = member.first_payment_month
    else:
        first_unpaid_year, first_unpaid_month = _increment_year_month(
            last_quota.year, last_quota.month)

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
