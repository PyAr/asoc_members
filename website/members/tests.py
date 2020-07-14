import datetime
import tempfile
import logassert
from io import BytesIO

from PIL import Image

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils.timezone import now, make_aware
from django.urls import reverse
from django.db.models.fields.files import ImageFieldFile

from members import logic, views, utils
from members.models import (
    Category,
    Member,
    Organization,
    Patron,
    Payment,
    PaymentStrategy,
    Person,
    Quota,
)
from .factories import (
    PatronFactory,
    QuotaFactory,
    PaymentFactory,
    PaymentStrategyFactory,
    MemberFactory,
    OrganizationFactory,
    PersonFactory,
)

DEFAULT_FEE = 100


def create_category():
    """Create a testing Category."""
    category = Category(name='testcategory', description="", fee=DEFAULT_FEE)
    category.save()
    return category


def create_member(
        first_payment_year=None, first_payment_month=None, patron=None, registration_date=None):
    """Create a testing Member."""
    first_payment_year = first_payment_year
    first_payment_month = first_payment_month
    category = create_category()
    return Member.objects.create(
        first_payment_year=first_payment_year, first_payment_month=first_payment_month,
        category=category, patron=patron, registration_date=registration_date)


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


def create_image_file_in_memory(width=150, height=150):
    file = BytesIO()
    image = Image.new('RGB', size=(width, height), color=(155, 0, 0))
    image.save(file, 'jpeg')
    file.name = 'image.jpg'
    file.seek(0)
    return file


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class SignupPagesTests(TestCase):

    def test_get_signup_page(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('signup_person'))
        self.assertContains(response, reverse('signup_organization'))
        self.assertTemplateUsed(response, 'members/signup_initial.html')

    def test_get_signup_person_page(self):
        response = self.client.get(reverse('signup_person'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'members/signup_form.html')

    def test_get_signup_org_page(self):
        response = self.client.get(reverse('signup_organization'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'members/signup_org_form.html')

    def test_signup_submit_success(self):
        # crear categoria
        cat = Category.objects.create(name='Activo', description='', fee=50)

        data = {
            'category': cat.pk,
            'first_name': 'Pepe',
            'last_name': "Pompin",
            'document_number': '124354656',
            'email': 'pepe@pomp.in',
            'nationality': 'Argentino',
            'marital_status': 'Soltero',
            'occupation': 'Python dev',
            'birth_date': '11/12/1999',
            'street_address': 'Calle False 123',
            'zip_code': '12345',
            'city': 'Córdoba',
            'province': 'Córdoba',
            'country': 'Argentina',
            'nickname': 'pepepin',
            'picture': create_image_file_in_memory()
        }
        response = self.client.get(reverse('signup_person'))
        response = self.client.post(reverse('signup_person'), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('signup_thankyou'))
        person = Person.objects.get(nickname='pepepin')
        self.assertEqual(person.first_name, 'Pepe')
        self.assertEqual(person.email, 'pepe@pomp.in')
        self.assertEqual(person.birth_date, datetime.date(1999, 12, 11))
        self.assertEqual(person.membership.category.pk, cat.pk)
        self.assertEqual(person.membership.patron.email, person.email)
        assert isinstance(person.picture, ImageFieldFile)

    def test_signup_submit_success_without_optionals(self):
        # crear categoria
        cat = Category.objects.create(name='Activo', description='', fee=50)

        data = {
            'category': cat.pk,
            'first_name': 'Pepe',
            'last_name': "Pompin",
            'document_number': '124354656',
            'email': 'pepe@pomp.in',
            'nationality': 'Argentino',
            'marital_status': 'Soltero',
            'occupation': 'Python dev',
            'birth_date': '11/12/1999',
            'street_address': 'Calle False 123',
            'zip_code': '12345',
            'city': 'Córdoba',
            'province': 'Córdoba',
            'country': 'Argentina',
        }
        response = self.client.get(reverse('signup_person'))
        response = self.client.post(reverse('signup_person'), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('signup_thankyou'))
        person = Person.objects.get(document_number='124354656')
        self.assertEqual(person.first_name, 'Pepe')
        self.assertEqual(person.email, 'pepe@pomp.in')
        self.assertEqual(person.birth_date, datetime.date(1999, 12, 11))

    def test_signup_submit_fail(self):
        # crear categoria
        cat = Category.objects.create(name='Activo', description='', fee=50)

        data = {
            'category': cat.pk,
            'first_name': 'Pepe',
            'last_name': "",
            'document_number': '124354656',
            'email': 'pepe@pomp.in',
            'nationality': 'Argentino',
            'marital_status': 'Soltero',
            'occupation': 'Python dev',
            'birth_date': '11/12/1999',
            'street_address': 'Calle False 123',
            'zip_code': '12345',
            'city': 'Córdoba',
            'province': 'Córdoba',
            'country': 'Argentina',
            'nickname': 'pepepin',
            'picture': create_image_file_in_memory(150, 100),
        }
        response = self.client.get(reverse('signup_person'))
        response = self.client.post(reverse('signup_person'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("last_name" in response.context["form"].errors)
        self.assertTrue("picture" in response.context["form"].errors)

    def test_signup_org_submit_success(self):
        random_text = 'oihihepiuhsidufhaohfiubiufwieufh'
        data = {
            'name': 'Orga',
            'contact_info': random_text,
            'document_number': "3056456530",
            'address': 'Calle False 123',
            'social_media': '@orga',
        }
        response = self.client.get(reverse('signup_organization'))
        response = self.client.post(reverse('signup_organization'), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('signup_thankyou'))
        orga = Organization.objects.get(name='Orga')
        self.assertEqual(orga.contact_info, random_text)

    def test_signup_org_submit_fail(self):
        random_text = 'oihihepiuhsidufhaohfiubiufwieufh'
        data = {
            'name': '',
            'contact_info': random_text,
            'document_number': "3056456530",
            'address': 'Calle False 123',
            'social_media': '@orga',
        }
        response = self.client.get(reverse('signup_organization'))
        response = self.client.post(reverse('signup_organization'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("name" in response.context["form"].errors)


class CreatePaymentTestCase(TestCase):
    """Tests for the simple payment creation."""

    def test_first_payment(self):
        # needed objects
        member = create_member(first_payment_year=2017, first_payment_month=5)
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
        member = create_member(first_payment_year=2017, first_payment_month=5)
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

    def test_from_specific_yearmonth(self):
        # needed objects
        member = create_member(first_payment_year=2017, first_payment_month=3)
        ps = create_payment_strategy()

        # create the payment
        amount = DEFAULT_FEE * 3
        logic.create_payment(member, now(), amount, ps, first_unpaid=(2017, 5))

        # check
        payed_fees = Quota.objects.all()
        self.assertEqual([(x.year, x.month) for x in payed_fees], [
            (2017, 5),
            (2017, 6),
            (2017, 7),
        ])

    def test_custom_fee(self):
        # needed objects
        member = create_member(first_payment_year=2017, first_payment_month=5)
        ps = create_payment_strategy()

        # create the payment
        custom_fee = DEFAULT_FEE // 2
        amount = custom_fee * 5
        logic.create_payment(member, now(), amount, ps, custom_fee=custom_fee)

        # check
        self.assertEqual(len(Quota.objects.all()), 5)


class CreateRecurringPaymentTestCase(TestCase):
    """Tests for the recurring payments creation."""

    def setUp(self):
        super().setUp()
        logassert.setup(self, "")

    def test_simple_empty(self):
        # needed objects
        payer_id = 'test@example.com'
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id=payer_id)
        member = create_member(patron=ps.patron, first_payment_year=2017, first_payment_month=5)

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
        member = create_member(patron=ps.patron, first_payment_year=2017, first_payment_month=5)

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
        create_member(patron=ps.patron, first_payment_year=2017, first_payment_month=5)

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
        member1 = create_member(patron=ps.patron, first_payment_year=2017, first_payment_month=5)
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id=payer_id2)
        member2 = create_member(patron=ps.patron, first_payment_year=2017, first_payment_month=5)

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
        create_member(patron=ps.patron, first_payment_year=2017, first_payment_month=5)

        # create two payments in different timestamps
        tstamp1 = make_aware(datetime.datetime(year=2017, month=2, day=1))
        tstamp2 = make_aware(datetime.datetime(year=2017, month=3, day=1))
        records = [
            {'timestamp': tstamp1, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
            {'timestamp': tstamp2, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
        ]
        logic.create_recurring_payments(records)
        assert len(Quota.objects.all()) == 2

        # now create other two, NOT overlapping
        tstamp3 = make_aware(datetime.datetime(year=2017, month=6, day=1))
        tstamp4 = make_aware(datetime.datetime(year=2017, month=7, day=1))
        tstamp5 = make_aware(datetime.datetime(year=2017, month=8, day=1))
        records = [
            {'timestamp': tstamp3, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
            {'timestamp': tstamp4, 'amount': DEFAULT_FEE, 'payer_id': payer_id},
            {'timestamp': tstamp5, 'amount': DEFAULT_FEE, 'payer_id': payer_id},

        ]
        logic.create_recurring_payments(records)

        # check we have no more payments created and proper error log (including the last
        # recorded and two new retrieved)
        self.assertEqual(len(Quota.objects.all()), 5)
        self.assertLoggedWarning(
            "Found exceeding payment limit", str(tstamp2), f'remaining: {len(records)}')

    def test_simple_custom_fee(self):
        # needed objects
        payer_id = 'test@example.com'
        ps = create_payment_strategy(platform=PaymentStrategy.MERCADO_PAGO, payer_id=payer_id)
        create_member(patron=ps.patron, first_payment_year=2017, first_payment_month=5)

        # create the payment
        tstamp = make_aware(datetime.datetime(year=2017, month=2, day=5))
        custom_fee = DEFAULT_FEE // 2
        records = [
            {'timestamp': tstamp, 'amount': custom_fee * 3, 'payer_id': payer_id},
        ]
        logic.create_recurring_payments(records, custom_fee=custom_fee)

        # check that payment got through ok, having 3 payments!
        self.assertEqual(len(Quota.objects.all()), 3)


class GetDebtStateTestCase(TestCase):
    """Tests for the debt state."""

    def test_previous_year(self):
        member = create_member(first_payment_year=2017, first_payment_month=8)
        ps = create_payment_strategy()
        logic.create_payment(member, now(), DEFAULT_FEE, ps)

        debt = logic.get_debt_state(member, 2018, 2)
        self.assertEqual(debt, [
            (2017, 9), (2017, 10), (2017, 11), (2017, 12),
            (2018, 1), (2018, 2)])

    def test_next_year(self):
        member = create_member(first_payment_year=2017, first_payment_month=6)
        ps = create_payment_strategy()
        logic.create_payment(member, now(), DEFAULT_FEE, ps)

        debt = logic.get_debt_state(member, 2016, 2)
        self.assertEqual(debt, [])

    def test_same_year_previous_month(self):
        member = create_member(first_payment_year=2017, first_payment_month=6)
        ps = create_payment_strategy()
        logic.create_payment(member, now(), DEFAULT_FEE, ps)

        debt = logic.get_debt_state(member, 2017, 2)
        self.assertEqual(debt, [])

    def test_same_year_next_month(self):
        member = create_member(first_payment_year=2017, first_payment_month=6)
        ps = create_payment_strategy()
        logic.create_payment(member, now(), DEFAULT_FEE, ps)

        debt = logic.get_debt_state(member, 2017, 11)
        self.assertEqual(debt, [
            (2017, 7), (2017, 8), (2017, 9), (2017, 10), (2017, 11)])

    def test_same_year_same_month(self):
        member = create_member(first_payment_year=2017, first_payment_month=6)
        ps = create_payment_strategy()
        logic.create_payment(member, now(), DEFAULT_FEE, ps)

        debt = logic.get_debt_state(member, 2017, 6)
        self.assertEqual(debt, [])

    def test_multiyear(self):
        member = create_member(first_payment_year=2017, first_payment_month=8)
        ps = create_payment_strategy()
        logic.create_payment(member, now(), DEFAULT_FEE, ps)

        debt = logic.get_debt_state(member, 2020, 2)
        self.assertEqual(debt, [
            (2017, 9), (2017, 10), (2017, 11), (2017, 12),
            (2018, 1), (2018, 2), (2018, 3), (2018, 4), (2018, 5), (2018, 6),
            (2018, 7), (2018, 8), (2018, 9), (2018, 10), (2018, 11), (2018, 12),
            (2019, 1), (2019, 2), (2019, 3), (2019, 4), (2019, 5), (2019, 6),
            (2019, 7), (2019, 8), (2019, 9), (2019, 10), (2019, 11), (2019, 12),
            (2020, 1), (2020, 2)])

    def test_no_payment_yet_previous_month(self):
        member = create_member(registration_date=datetime.date(2017, 5, 13))
        debt = logic.get_debt_state(member, 2017, 1)
        self.assertEqual(debt, [])

    def test_no_payment_yet_registration_month(self):
        member = create_member(registration_date=datetime.date(2017, 5, 13))
        debt = logic.get_debt_state(member, 2017, 5)
        self.assertEqual(debt, [(2017, 5)])

    def test_no_payment_yet_several_months(self):
        member = create_member(registration_date=datetime.date(2017, 5, 13))
        debt = logic.get_debt_state(member, 2017, 8)
        self.assertEqual(debt, [(2017, 5), (2017, 6), (2017, 7), (2017, 8)])


class BuildDebtStringTestCase(TestCase):
    """Tests for the string debt building utility."""

    def test_empty(self):
        result = utils.build_debt_string([])
        self.assertEqual(result, "-")

    def test_1(self):
        result = utils.build_debt_string([(2018, 8)])
        self.assertEqual(result, "1 (2018-08)")

    def test_2(self):
        result = utils.build_debt_string([(2018, 8), (2018, 9)])
        self.assertEqual(result, "2 (2018-08, 2018-09)")

    def test_3(self):
        result = utils.build_debt_string([(2018, 8), (2018, 9), (2018, 10)])
        self.assertEqual(result, "3 (2018-08, 2018-09, 2018-10)")

    def test_exceeding(self):
        result = utils.build_debt_string([(2018, 8), (2018, 9), (2018, 10), (2018, 11)])
        self.assertEqual(result, "4 (2018-08, 2018-09, 2018-10, ...)")


class MatchFactoryWithModelTestCase(TestCase):
    """Tests for checking if factory match the model."""
    def test_for_match_fields_with_factory(self):
        ps = create_payment_strategy()
        patron = PatronFactory.build()
        member = MemberFactory.build()
        person = PersonFactory.build()
        organization = OrganizationFactory.build()
        payment_strategy = PaymentStrategyFactory.build(patron=patron)
        payment = PaymentFactory.build(strategy=ps, amount=DEFAULT_FEE)
        quota = QuotaFactory.build(payment=payment, member=member)
        assert isinstance(patron, Patron)
        assert isinstance(member, Member)
        assert isinstance(person, Person)
        assert isinstance(organization, Organization)
        assert isinstance(payment_strategy, PaymentStrategy)
        assert isinstance(payment, Payment)
        assert isinstance(quota, Quota)


class MembersReportTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username='testuser', password='12345', email='1@1.com')
        self.client.force_login(user)
        self.addCleanup(self.client.logout)

    def test_get_members_list_page(self):
        response = self.client.get(reverse('members_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'members/members_list.html')

    def test_get_member_detail_page(self):
        member = create_member(first_payment_year=2017, first_payment_month=5)
        response = self.client.get(reverse('member_detail', kwargs={"pk": member.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'members/member_detail.html')

    def test_last_payments_none(self):
        member = create_member()
        info = views.MemberDetailView()._get_last_payments(member)
        self.assertEqual(info, [])

    def test_last_payments_one(self):
        member = create_member(first_payment_year=2017, first_payment_month=5)
        ps = create_payment_strategy()
        amount = 100
        tstamp = datetime.datetime(2018, 3, 22, 14, 32, 11)
        logic.create_payment(member, tstamp, amount, ps)
        info = views.MemberDetailView()._get_last_payments(member)
        self.assertEqual(info, [
            {
                'title': 'Transfer x 100.00',
                'timestamp': '2018-03-22 14:32:11',
                'quotas': '2017-05',
            }
        ])

    def test_last_payments_several(self):
        member = create_member(first_payment_year=2017, first_payment_month=5)
        ps = create_payment_strategy()

        # payment 1
        amount = 100
        tstamp = datetime.datetime(2018, 3, 22, 14, 32, 11)
        logic.create_payment(member, tstamp, amount, ps)

        # payment 2
        amount = 500
        tstamp = datetime.datetime(2020, 3, 22, 14, 32, 11)  # mixed tstamp on purpose!!
        logic.create_payment(member, tstamp, amount, ps)

        # payment 3
        amount = 300
        tstamp = datetime.datetime(2019, 3, 22, 14, 32, 11)
        logic.create_payment(member, tstamp, amount, ps)

        info = views.MemberDetailView()._get_last_payments(member)
        self.assertEqual(info, [
            {
                'title': 'Transfer x 500.00',
                'timestamp': '2020-03-22 14:32:11',
                'quotas': '2017-06, 2017-07, 2017-08, 2017-09, 2017-10',
            },
            {
                'title': 'Transfer x 300.00',
                'timestamp': '2019-03-22 14:32:11',
                'quotas': '2017-11, 2017-12, 2018-01',
            },
            {
                'title': 'Transfer x 100.00',
                'timestamp': '2018-03-22 14:32:11',
                'quotas': '2017-05',
            },
        ])

    def test_last_payments_limited(self):
        member = create_member(first_payment_year=2017, first_payment_month=5)
        ps = create_payment_strategy()

        # 15 payments
        amount = 100
        for second in range(15):
            tstamp = datetime.datetime(2020, 3, 22, 14, 32, second)
            logic.create_payment(member, tstamp, amount, ps)

        # it should show only 12, still ordered
        info = views.MemberDetailView()._get_last_payments(member)
        self.assertEqual(len(info), 12)
        self.assertEqual(info[0]['timestamp'], '2020-03-22 14:32:14')


class MemberTests(TestCase):

    def _create_member(self, **kwargs):
        """Create a not-yet-member with good defaults, accepting changes."""
        category_name = kwargs.pop('category_name', Category.ACTIVE)
        params = {
            'category': Category.objects.get(name=category_name),
            'first_payment_month': 8,
            'first_payment_year': 2015,
            'has_student_certificate': False,
            'has_subscription_letter': True,
            'has_collaborator_acceptance': False,
        }
        params = {k: kwargs.pop(k, v) for k, v in params.items()}
        member = Member.objects.create(**params)

        # create the related person
        params = {
            'membership': member,
            'nickname': 'test-nick',
            'picture': 'fake-pic',
        }
        params = {k: kwargs.pop(k, v) for k, v in params.items()}
        Person.objects.create(**params)

        assert not kwargs, kwargs  # would indicate a misuse of the parameters
        return member

    def test_missing_info_all_perfect(self):
        member = self._create_member()

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertFalse(missing)

        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertFalse(missing)

    def test_missing_info_student_without_certificate(self):
        member = self._create_member(category_name=Category.STUDENT, has_student_certificate=False)

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertEqual(missing, {'missing_student_certif'})

        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertEqual(missing, {'missing_student_certif'})

    def test_missing_info_student_with_certificate(self):
        member = self._create_member(category_name=Category.STUDENT, has_student_certificate=True)

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertFalse(missing)

        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertFalse(missing)

    def test_missing_info_collaborator_not_accepted(self):
        member = self._create_member(
            category_name=Category.COLLABORATOR, has_collaborator_acceptance=False)

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertEqual(missing, {'missing_collab_accept'})

        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertEqual(missing, {'missing_collab_accept'})

    def test_missing_info_collaborator_accepted(self):
        member = self._create_member(
            category_name=Category.COLLABORATOR, has_collaborator_acceptance=True)

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertFalse(missing)

        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertFalse(missing)

    def test_missing_info_missing_picture(self):
        member = self._create_member(picture='')

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertEqual(missing, {'missing_picture'})

        # picture is not needed to consider the member as "complete"
        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertFalse(missing)

    def test_missing_info_denied_picture(self):
        member = self._create_member(picture=False)

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertFalse(missing)

        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertFalse(missing)

    def test_missing_info_missing_nickname(self):
        member = self._create_member(nickname='')

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertEqual(missing, {'missing_nickname'})

        # nickname is not needed to consider the member as "complete"
        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertFalse(missing)

    def test_missing_info_missing_signed_letter(self):
        member = self._create_member(has_subscription_letter=False)

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertEqual(missing, {'missing_signed_letter'})

        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertEqual(missing, {'missing_signed_letter'})

    def test_missing_info_missing_payment_payingtype(self):
        member = self._create_member(first_payment_year=None, first_payment_month=None)

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertEqual(missing, {'missing_payment'})

        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertFalse(missing)

    def test_missing_info_missing_payment_notpayingtype(self):
        member = self._create_member(
            category_name=Category.TEENAGER, first_payment_year=None, first_payment_month=None)

        missing = {k for k, v in member.get_missing_info().items() if v}
        self.assertFalse(missing)

        missing = {k for k, v in member.get_missing_info(for_approval=True).items() if v}
        self.assertFalse(missing)
