import datetime

import logassert
from django.test import TestCase
from django.utils.timezone import now, make_aware

from members import logic
from members.models import Member, Patron, Category, PaymentStrategy, Quota


DEFAULT_FEE = 100


def create_category():
    """Create a testing Category."""
    category = Category(name='testcategory', description="", fee=DEFAULT_FEE)
    category.save()
    return category


def create_member(first_payment_year=None, first_payment_month=None, patron=None):
    """Create a testing Member."""
    first_payment_year = first_payment_year or 2017
    first_payment_month = first_payment_month or 5
    category = create_category()
    return Member.objects.create(
        first_payment_year=first_payment_year, first_payment_month=first_payment_month,
        category=category, patron=patron)


def create_patron(email=None):
    """Create a testing Patron."""
    email = "patron-email" if email is None else email
    return Patron.objects.create(name="patron-name", email=email, comments="")


def create_payment_strategy(platform=None, payer_id=None):
    """Create a testing PaymentStrategy."""
    patron = create_patron(email=payer_id)
    platform = PaymentStrategy.TRANSFER if platform is None else platform
    payer_id = "" if payer_id is None else payer_id
    return PaymentStrategy.objects.create(
        platform=platform, id_in_platform=payer_id, patron=patron)


class CreatePaymentTestCase(TestCase):
    """Tests for the simple payment creation."""

    def test_first_payment(self):
        # needed objects
        member = create_member()
        ps = create_payment_strategy()

        # create the payment
        amount = DEFAULT_FEE
        logic.create_payment(member, now(), amount, ps)

        # check
        (payed_fee,) = Quota.objects.all()
        self.assertEqual(payed_fee.year, member.first_payment_year)
        self.assertEqual(payed_fee.month, member.first_payment_month)
        self.assertEqual(payed_fee.member, member)

    def test_second_payment(self):
        # needed objects
        member = create_member(first_payment_year=2017, first_payment_month=3)
        ps = create_payment_strategy()
        amount = DEFAULT_FEE
        logic.create_payment(member, now(), amount, ps)

        # create the second payment
        logic.create_payment(member, now(), amount, ps)

        # check
        (payed_fee1, payed_fee2) = Quota.objects.all()
        self.assertEqual(payed_fee1.year, 2017)
        self.assertEqual(payed_fee1.month, 3)
        self.assertEqual(payed_fee1.member, member)
        self.assertEqual(payed_fee2.year, 2017)
        self.assertEqual(payed_fee2.month, 4)
        self.assertEqual(payed_fee2.member, member)

    def test_several_months(self):
        # needed objects
        member = create_member(first_payment_year=2017, first_payment_month=3)
        ps = create_payment_strategy()

        # create the payment
        amount = DEFAULT_FEE * 3
        logic.create_payment(member, now(), amount, ps)

        # check
        payed_fees = Quota.objects.all()
        self.assertEqual([(x.year, x.month) for x in payed_fees], [
            (2017, 3),
            (2017, 4),
            (2017, 5),
        ])

    def test_crossing_years(self):
        # needed objects
        member = create_member(first_payment_year=2017, first_payment_month=11)
        ps = create_payment_strategy()

        # create the payment
        amount = DEFAULT_FEE * 15
        logic.create_payment(member, now(), amount, ps)

        # check
        payed_fees = Quota.objects.all()
        self.assertEqual([(x.year, x.month) for x in payed_fees], [
            (2017, 11),
            (2017, 12),
            (2018, 1),
            (2018, 2),
            (2018, 3),
            (2018, 4),
            (2018, 5),
            (2018, 6),
            (2018, 7),
            (2018, 8),
            (2018, 9),
            (2018, 10),
            (2018, 11),
            (2018, 12),
            (2019, 1),
        ])

    def test_not_exact_amount_small(self):
        # needed objects
        member = create_member()
        ps = create_payment_strategy()

        # create the payment
        amount = DEFAULT_FEE * 1.0001
        logic.create_payment(member, now(), amount, ps)

        # check
        (payed_fee,) = Quota.objects.all()
        self.assertEqual(payed_fee.year, member.first_payment_year)
        self.assertEqual(payed_fee.month, member.first_payment_month)
        self.assertEqual(payed_fee.member, member)

    def test_not_exact_amount_big(self):
        # needed objects
        member = create_member()
        ps = create_payment_strategy()

        # create the payment
        amount = DEFAULT_FEE * 1.1
        self.assertRaises(ValueError, logic.create_payment, member, now(), amount, ps)


class CreateRecurringPaymentTestCase(TestCase):
    """Tests for the recurring payments creation."""

    def setUp(self):
        super().setUp()
        logassert.setup(self, "")

    def test_simple_empty(self):
        # needed objects
        payer_id = 'test@example.com'
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id=payer_id)
        member = create_member(patron=ps.patron)

        # create the payment
        tstamp = make_aware(datetime.datetime(year=2017, month=2, day=5))
        records = [
            {'timestamp': tstamp, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
        ]
        logic.create_recurring_payments(records)

        # check
        self.assertLoggedInfo("Creating recurring payments", payer_id, str(member), "2017, 2, 5")
        (payed_fee,) = Quota.objects.all()
        self.assertEqual(payed_fee.year, member.first_payment_year)
        self.assertEqual(payed_fee.month, member.first_payment_month)
        self.assertEqual(payed_fee.member, member)

    def test_simple_previous_payments(self):
        # needed objects
        payer_id = 'test@example.com'
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id=payer_id)
        member = create_member(patron=ps.patron)

        # create three payments in different timestamps
        tstamp1 = make_aware(datetime.datetime(year=2017, month=2, day=5))
        tstamp2 = make_aware(datetime.datetime(year=2017, month=2, day=6))
        tstamp3 = make_aware(datetime.datetime(year=2017, month=2, day=7))
        records = [
            {'timestamp': tstamp1, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
            {'timestamp': tstamp2, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
            {'timestamp': tstamp3, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
        ]
        logic.create_recurring_payments(records)

        # now create other two, overlapping
        tstamp4 = make_aware(datetime.datetime(year=2017, month=2, day=8))
        records = [
            {'timestamp': tstamp3, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
            {'timestamp': tstamp4, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
        ]
        logic.create_recurring_payments(records)

        # check we have four payments
        all_quotas = Quota.objects.all()
        self.assertEqual(len(all_quotas), 4)
        self.assertEqual(
            sorted(q.payment.timestamp for q in all_quotas), [tstamp1, tstamp2, tstamp3, tstamp4])
        self.assertLoggedInfo(
            "Creating recurring payments", payer_id, str(member), "2017, 2, 8")

    def test_simple_everything_previous(self):
        # needed objects
        payer_id = 'test@example.com'
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id=payer_id)
        create_member(patron=ps.patron)

        # create two payments in different timestamps
        tstamp1 = make_aware(datetime.datetime(year=2017, month=2, day=5))
        tstamp2 = make_aware(datetime.datetime(year=2017, month=2, day=6))
        records = [
            {'timestamp': tstamp1, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
            {'timestamp': tstamp2, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
        ]
        logic.create_recurring_payments(records)

        # now create another, repeated
        records = [
            {'timestamp': tstamp2, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
        ]
        logic.create_recurring_payments(records)

        # check we have four payments
        all_quotas = Quota.objects.all()
        self.assertEqual(len(all_quotas), 2)
        self.assertEqual(
            sorted(q.payment.timestamp for q in all_quotas), [tstamp1, tstamp2])

    def test_multiple_payers(self):
        # needed objects
        payer_id1 = 'test@example.com'
        payer_id2 = 'other@example.com'
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id=payer_id1)
        member1 = create_member(patron=ps.patron)
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id=payer_id2)
        member2 = create_member(patron=ps.patron)

        # create the payment
        tstampA = make_aware(datetime.datetime(year=2017, month=2, day=5))
        tstampB = make_aware(datetime.datetime(year=2017, month=2, day=6))
        tstampC = make_aware(datetime.datetime(year=2017, month=2, day=7))
        records = [
            {'timestamp': tstampA, 'amount': DEFAULT_FEE, 'payer_id': payer_id1},
            {'timestamp': tstampC, 'amount': DEFAULT_FEE, 'payer_id': payer_id1},
            {'timestamp': tstampB, 'amount': DEFAULT_FEE, 'payer_id': payer_id2},
            {'timestamp': tstampA, 'amount': DEFAULT_FEE, 'payer_id': payer_id2},
        ]
        logic.create_recurring_payments(records)

        # check
        self.assertLoggedInfo(
            "Creating recurring payments", payer_id1, str(member1), "2017, 2, 5", "2017, 2, 7")
        self.assertLoggedInfo(
            "Creating recurring payments", payer_id2, str(member2), "2017, 2, 5", "2017, 2, 6")
        payed_fees = Quota.objects.all()
        self.assertEqual(payed_fees[0].member, member1)
        self.assertEqual(payed_fees[0].payment.timestamp, tstampA)
        self.assertEqual(payed_fees[1].member, member1)
        self.assertEqual(payed_fees[1].payment.timestamp, tstampC)
        self.assertEqual(payed_fees[2].member, member2)
        self.assertEqual(payed_fees[2].payment.timestamp, tstampA)
        self.assertEqual(payed_fees[3].member, member2)
        self.assertEqual(payed_fees[3].payment.timestamp, tstampB)

    def test_strategy_not_found(self):
        # needed objects
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id='foo')
        create_member(patron=ps.patron)

        # create the payment
        tstamp = make_aware(datetime.datetime(year=2017, month=2, day=5))
        records = [
            {'timestamp': tstamp, 'amount': DEFAULT_FEE, 'payer_id': 'bar'},
        ]
        logic.create_recurring_payments(records)

        # check
        self.assertEqual(len(Quota.objects.all()), 0)
        self.assertLoggedError("PaymentStrategy not found", "bar")

    def test_sanity_check_multiple_patrons(self):
        # create two members for the same patron, something we don't
        # support for recurring payments
        payer_id = 'test@example.com'
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id=payer_id)
        create_member(patron=ps.patron)
        create_member(patron=ps.patron)

        # create the payment
        tstamp = make_aware(datetime.datetime(year=2017, month=2, day=5))
        records = [
            {'timestamp': tstamp, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
        ]
        logic.create_recurring_payments(records)

        # check
        self.assertEqual(len(Quota.objects.all()), 0)
        self.assertLoggedError("Found more than one member for Patron", ps.patron.name)

    def test_no_payment_match(self):
        # needed objects
        payer_id = 'test@example.com'
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id=payer_id)
        create_member(patron=ps.patron)

        # create two payments in different timestamps
        tstamp1 = make_aware(datetime.datetime(year=2017, month=2, day=5))
        tstamp2 = make_aware(datetime.datetime(year=2017, month=2, day=6))
        records = [
            {'timestamp': tstamp1, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
            {'timestamp': tstamp2, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
        ]
        logic.create_recurring_payments(records)
        assert len(Quota.objects.all()) == 2

        # now create other two, NOT overlapping
        tstamp3 = make_aware(datetime.datetime(year=2017, month=2, day=7))
        tstamp4 = make_aware(datetime.datetime(year=2017, month=2, day=8))
        records = [
            {'timestamp': tstamp3, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
            {'timestamp': tstamp4, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
        ]
        logic.create_recurring_payments(records)

        # check we have no more payments created and proper error log (including the last
        # recorded and two new retrieved)
        self.assertEqual(len(Quota.objects.all()), 2)
        self.assertLoggedError("Payment not found", str(tstamp2), "2017, 2, 7", "2017, 2, 8")
