from django.test import TestCase
from django.utils.timezone import now

from members import logic
from members.models import Member, Patron, Category, PaymentStrategy, Quota


DEFAULT_FEE = 100


def create_category():
    """Create a testing Category."""
    category = Category(name='testcategory', description="", fee=DEFAULT_FEE)
    category.save()
    return category


def create_member(first_payment_year=None, first_payment_month=None):
    """Create a testing Member."""
    first_payment_year = first_payment_year or 2017
    first_payment_month = first_payment_month or 5
    category = create_category()
    return Member.objects.create(
        first_payment_year=first_payment_year, first_payment_month=first_payment_month,
        category=category)


def create_patron():
    """Create a testing Patron."""
    return Patron.objects.create(name="patron-name", email="patron-email", comments="")


def create_payment_strategy():
    """Create a testing PaymentStrategy."""
    patron = create_patron()
    return PaymentStrategy.objects.create(
        platform=PaymentStrategy.TRANSFER, id_in_platform="", patron=patron)


class CreatePaymentTestCase(TestCase):
    """Tests for the Member model."""

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
