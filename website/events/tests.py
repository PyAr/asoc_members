from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError

from events.constants import (
    CANT_CHANGE_CLOSE_EVENT_MESSAGE,
    DUPLICATED_SPONSOR_CATEGORY_MESSAGE,
    INVOICE_APPOVED_MESSAGE,
    INVOICE_SET_COMPLETE_PAYMENT_MESSAGE,
    INVOICE_SET_PARTIAL_PAYMENT_MESSAGE,
    MUST_EXISTS_SPONSOR_MESSAGE,
    MUST_EXISTS_SPONSOR_CATEGORY_MESSAGE,
    MUST_BE_ACCOUNT_OWNER_MESSAGE,
    MUST_BE_ORGANIZER_MESSAGE,
    MUST_BE_EVENT_ORGANIZAER_MESSAGE,
    ORGANIZER_MAIL_NOTOFICATION_MESSAGE,
    SPONSOR_STATE_UNBILLED,
    SPONSOR_STATE_CLOSED,
    SPONSOR_STATE_COMPLETELY_PAID,
    SPONSOR_STATE_INVOICED,
    SPONSOR_STATE_CHECKED,
    SPONSOR_STATE_PARTIALLY_PAID,
    SPONSORING_SUCCESSFULLY_CLOSE_MESSAGE
)
from events.helpers.notifications import email_notifier
from events.helpers.permissions import (
    ORGANIZER_GROUP_NAME,
    organizer_permissions
)
from events.helpers.task import (
    _not_approved_invoices,
    calculate_organizer_task,
    calculate_super_user_task,
    Task
)
from events.helpers.sponsoring_pending import (
    PendingSponsoring,
    pending_sponsoring,
    calculate_sponsoring_pending,
)
from events.helpers.tests import (
    associate_events_organizers,
    CustomAssertMethods,
    sponsor_data,
    provider_data,
    create_user_set,
    create_event_set,
    create_invoice_affect_set,
    create_organizer_set,
    create_sponsors_set,
    create_sponsoring_set,
    create_sponsoring_invoice,
    create_provider,
    create_provider_expense,
    create_organizer_refund,
)

from events.middleware import set_current_user
from events.models import (
    BankAccountData,
    Event,
    Organizer,
    Payment,
    Provider,
    Sponsor,
    SponsorCategory,
    Sponsoring,
    ProviderExpense,
    OrganizerRefund,
    validate_cuit,
)
from io import StringIO
from unittest.mock import patch

User = get_user_model()
test_task = Task('descripcion', 'url', timezone.now())


class MockSuperUser:
    def has_perm(self, perm):
        return True


def admin_event_associate_organizers_post_data(event, organizers):
    """Create data to send to events admin url to associate organizers to event."""
    data = {
        'name': [event.name],
        'commission': [str(event.commission)],
        'category': [''],
        'start_date': [''],
        'place': [''],

        'event_organizers-TOTAL_FORMS': [str(len(organizers))],
        'event_organizers-INITIAL_FORMS': ['0'],
        'event_organizers-MIN_NUM_FORMS': ['0'],
        'event_organizers-MAX_NUM_FORMS': ['1000'],

        'event_organizers-__prefix__-id': [''],
        'event_organizers-__prefix__-event': ['1'],
        'event_organizers-__prefix__-organizer': [''],
        '_save': ['Save']
    }

    association_num = 0
    for organizer in organizers:
        prefix = f"event_organizers-{association_num}-"
        data[prefix + 'id'] = ['']
        data[prefix + 'event'] = [str(event.pk)]
        data[prefix + 'organizer'] = [str(organizer.pk)]
        association_num = association_num + 1

    return data


class EmailTest(TestCase, CustomAssertMethods):
    def setUp(self):
        create_user_set()
        user = User.objects.first()
        create_event_set(user)

    def test_send_email_after_create_sponsor(self):
        self.client.login(username='organizer01', password='organizer01')

        response = self.client.post(reverse('sponsor_create'), data=sponsor_data)
        self.assertEqual(response.status_code, 302)
        count = User.objects.filter(is_superuser=True).exclude(email__exact='').count()
        self.assertEqual(len(mail.outbox), count)
        self.assertEqual(mail.outbox[0].subject,
                         render_to_string('mails/sponsor_just_created_subject.txt'))

    def test_send_email_after_enable_sponsor(self):
        self.client.login(username='administrator', password='administrator')
        create_sponsors_set()
        sponsor = Sponsor.objects.filter(enabled=False).first()
        response = self.client.post(reverse('sponsor_set_enabled', kwargs={'pk': sponsor.pk}))
        self.assertEqual(response.status_code, 302)

        self.assertEqual(mail.outbox[0].subject,
                         render_to_string('mails/sponsor_just_enabled_subject.txt'))

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_send_email_after_create_invoice(self, mock_save):
        mock_save.return_value = 'invoice.pdf'
        create_organizer_set()
        associate_events_organizers()
        create_sponsoring_set(auto_create_sponsors_set=True)
        event = Event.objects.filter(name='MyTest01').first()
        sponsoring = Sponsoring.objects.filter(sponsorcategory__event=event).first()
        # To complete the test we need, an event, an enabled sponsor, event_category
        self.client.login(username='administrator', password='administrator')
        data = {
            'amount': '40000',
            'document': StringIO('test'),
        }
        url = reverse('sponsoring_invoice_create', kwargs={'pk': sponsoring.pk})
        response = self.client.post(url, data)

        redirect_url = reverse('sponsoring_detail', kwargs={'pk': sponsoring.pk})
        self.assertRedirects(response, redirect_url)
        count = event.organizers.count()
        self.assertEqual(len(mail.outbox), count)
        self.assertEqual(mail.outbox[0].subject,
                         render_to_string('mails/invoice_just_created_subject.txt'))

    def test_send_email_after_create_invoice_affect(self):
        create_organizer_set()
        associate_events_organizers()
        invoice = create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        invoice.invoice_ok = True
        invoice.save()

        url = reverse('sponsoring_invoice_affect_create', kwargs={'pk': invoice.pk})
        # To complete the test we need, an event, an enabled sponsor, event_category
        self.client.login(username='administrator', password='administrator')
        data = {
            'amount': '1000',
            'category': 'Pay',
            'document': StringIO('test'),
        }
        response = self.client.post(url, data)

        redirect_url = reverse('sponsoring_detail', kwargs={'pk': invoice.sponsoring.pk})
        self.assertRedirects(response, redirect_url)
        count = User.objects.filter(is_superuser=True).exclude(email__exact='').count()
        self.assertEqual(len(mail.outbox), count)
        self.assertEqual(mail.outbox[0].subject,
                         render_to_string('mails/invoice_affect_just_created_subject.txt'))

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_send_email_after_create_provider_expense(self, mock_save):
        create_organizer_set()
        associate_events_organizers()
        create_provider()
        mock_save.return_value = 'expense.pdf'
        provider_expense_data = {
            'provider': Provider.objects.first().pk,
            'amount': '1200',
            'invoice_type': 'A',
            'invoice_date': '12/01/2019',
            'invoice': StringIO('test'),
            'description': 'test'
        }
        url = reverse(
            'provider_expense_create',
            kwargs={'event_pk': Event.objects.filter(name='MyTest01').first().pk}
        )
        self.client.login(username='organizer01', password='organizer01')
        self.client.post(url, data=provider_expense_data)
        count = User.objects.filter(is_superuser=True).exclude(email__exact='').count()
        self.assertEqual(len(mail.outbox), count)
        self.assertEqual(mail.outbox[0].subject,
                         render_to_string('mails/expense_just_created_subject.txt'))

    def test_send_email_after_create_sponsoring(self):
        create_organizer_set()
        associate_events_organizers()
        create_sponsors_set()
        sponsor = Sponsor.objects.filter(enabled=True).first()
        event = Event.objects.filter(name='MyTest01').first()
        sponsor_category = SponsorCategory.objects.filter(event=event).first()
        url = reverse('sponsoring_create', kwargs={'event_pk': event.pk})
        # To complete the test we need, an event, an enabled sponsor, event_category
        self.client.login(username='organizer02', password='organizer02')

        data = {
            'comments': ''
        }
        data['sponsorcategory'] = sponsor_category.pk
        data['sponsor'] = sponsor.pk
        response = self.client.post(url, data)

        sponsoring = Sponsoring.objects.last()
        redirect_url = reverse('sponsoring_detail', kwargs={'pk': sponsoring.pk})
        self.assertRedirects(response, redirect_url)
        count = User.objects.filter(is_superuser=True).exclude(email__exact='').count()
        self.assertEqual(len(mail.outbox), count)
        self.assertEqual(mail.outbox[0].subject,
                         render_to_string('mails/sponsoring_just_created_subject.txt'))

    def test_send_email_after_register_organizer(self):
        # Login client with super user
        self.client.login(username='administrator', password='administrator')

        # Send request
        data = {
            'username': 'juanito',
            'email': 'new_organizer@pyar.com',
        }
        response = self.client.post(reverse('organizer_signup'), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         render_to_string('mails/organizer_just_created_subject.txt'))

        self.assertContainsMessage(response, ORGANIZER_MAIL_NOTOFICATION_MESSAGE)

    def test_send_organizer_associated_to_event_sends_mails_with_subject(self):
        """ Testing that function 'send_organizer_associated_to_event' sends emails to the
        listed organizers with the correct subject."""

        event = Event.objects.filter(name='MyTest01').first()
        create_organizer_set()

        email_notifier.send_organizer_associated_to_event(
            event,
            Organizer.objects.all(),
            {'domain': 'testserver', 'protocol': 'http'}
        )
        self.assertEqual(len(mail.outbox), Organizer.objects.all().count())

        send_to = []
        for email in mail.outbox:
            send_to.extend(email.to)
            self.assertEqual(email.subject,
                             render_to_string('mails/organizer_associated_to_event_subject.txt'))

        self.assertIn('test01@test.com', send_to)
        self.assertIn('test02@test.com', send_to)


class SingnupOrginizerTest(TestCase):
    def setUp(self):
        create_user_set()

    def test_organizer_signup_redirects_without_perms(self):
        response = self.client.get(reverse('organizer_signup'))
        # Login client with not superuser
        self.client.login(username='organizer01', password='organizer01')

        # View redirect.
        self.assertEqual(response.status_code, 302)

        # And redirect to login.
        redirect_to_login_url = reverse('login') + '?next=' + reverse('organizer_signup')
        self.assertEqual(response.url, redirect_to_login_url)

    def test_user_with_add_organizer_perm_no_redirects(self):
        # Login client with super_organizer
        self.client.login(username='superOrganizer01', password='superOrganizer01')

        response = self.client.get(reverse('organizer_signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'organizers/organizer_signup.html')

    def test_organizer_created_on_signup(self):
        self.client.login(username='superOrganizer01', password='superOrganizer01')
        url = reverse('organizer_signup')
        data = {
            'email': 'test@mail.com',
            'username': 'organizador_test'
        }
        self.client.post(url, data=data)
        self.assertTrue(
            Organizer.objects.filter(user=User.objects.get(username='organizador_test')).exists()
        )

    def test_created_organizer_associates_with_group(self):
        self.client.login(username='superOrganizer01', password='superOrganizer01')
        url = reverse('organizer_signup')
        data = {
            'email': 'test@mail.com',
            'username': 'organizador_test'
        }
        self.client.post(url, data=data)

        user = User.objects.get(username='organizador_test')
        group = Group.objects.get(name=ORGANIZER_GROUP_NAME)
        self.assertIn(group, user.groups.all())

    def test_organizer_group_has_perms(self):
        group = Group.objects.get(name=ORGANIZER_GROUP_NAME)
        organizer_perms = organizer_permissions()
        group_permissions = group.permissions.all()
        for perm in organizer_perms:
            self.assertIn(perm, group_permissions)


class EventAdminTest(TestCase):
    def setUp(self):
        create_user_set()
        user = User.objects.first()
        create_event_set(user)
        create_organizer_set()

    @patch('events.helpers.notifications.EmailNotification.send_organizer_associated_to_event')
    def test_on_organizer_associate_to_event_call_mail_function(self, send_email_function):
        event = Event.objects.filter(name='MyTest01').first()

        url = reverse('admin:events_event_change', kwargs={'object_id': event.pk})
        self.client.login(username='administrator', password='administrator')

        organizers = []
        for organizer in Organizer.objects.all():
            organizers.append(organizer)

        data = admin_event_associate_organizers_post_data(event, organizers)
        self.client.post(url, data=data)
        send_email_function.assert_called_once_with(
            event,
            organizers,
            {'domain': 'testserver', 'protocol': 'http'}
        )


class BankAccountDataTest(TestCase, CustomAssertMethods):
    account_data = {
        'organization_name': 'Pablo',
        'document_number': '20-21321265-7',
        'bank_entity': 'Banco Rio',
        'account_type': 'CC',
        'account_number': '4',
        'cbu': '2850590940090418135201'
    }

    def setUp(self):
        create_user_set()
        user = User.objects.first()
        create_event_set(user)

        create_organizer_set()

    def test_must_be_organizer_to_create_banck_account(self):
        organizer = Organizer.objects.get(user__username="organizer01")
        url = reverse('organizer_create_bank_account_data', kwargs={'pk': organizer.pk})
        self.client.login(username='noOrganizer', password='noOrganizer')
        response = self.client.post(url, data=self.account_data)
        expected_url = reverse('events_home')
        self.assertRedirects(response, expected_url)
        self.assertContainsMessage(response, MUST_BE_ORGANIZER_MESSAGE)

    def test_must_be_owner_to_update_banck_account(self):
        account = BankAccountData.objects.create(**self.account_data)
        organizer02 = Organizer.objects.get(user__username="organizer02")

        organizer = Organizer.objects.get(user__username="organizer01")
        organizer.account_data = account
        organizer.save()
        self.client.login(username='organizer02', password='organizer02')
        url = reverse('organizer_update_bank_account_data', kwargs={'pk': account.pk})

        data = self.account_data
        data['organization_name'] = 'Andres'

        response = self.client.post(url, data=data)
        expected_url = reverse('organizer_detail', kwargs={'pk': organizer02.pk})
        self.assertRedirects(response, expected_url)
        self.assertContainsMessage(response, MUST_BE_ACCOUNT_OWNER_MESSAGE)

    def test_account_create_is_associated_with_organizer(self):
        organizer = Organizer.objects.get(user__username="organizer01")
        self.assertIsNone(organizer.account_data)
        url = reverse('organizer_create_bank_account_data', kwargs={'pk': organizer.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url, data=self.account_data)
        expected_url = reverse('organizer_detail', kwargs={'pk': organizer.pk})
        self.assertRedirects(response, expected_url)
        organizer.refresh_from_db()
        self.assertIsNotNone(organizer.account_data)


class EventViewsTest(TestCase, CustomAssertMethods):
    def setUp(self):
        create_user_set()
        user = User.objects.first()
        create_event_set(user)
        create_organizer_set()
        associate_events_organizers()

    def test_event_detail_redirects_no_associated_organizer(self):
        event = Event.objects.filter(name='MyTest02').first()
        url = reverse('event_detail', kwargs={'pk': event.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.get(url)
        expected_url = reverse('event_list')
        self.assertRedirects(response, expected_url)
        self.assertContainsMessage(response, MUST_BE_EVENT_ORGANIZAER_MESSAGE)

    def test_event_change_redirects_on_closed_event(self):
        event = Event.objects.filter(name='MyTest01').first()
        event.close = True
        event.save()

        url = reverse('event_change', kwargs={'pk': event.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.get(url)

        expected_url = reverse('event_detail', kwargs={'pk': event.pk})
        self.assertRedirects(response, expected_url)
        self.assertContainsMessage(response, CANT_CHANGE_CLOSE_EVENT_MESSAGE)

    def test_cant_duplicate_sponsor_category(self):
        set_current_user(User.objects.filter(username='organizer01').first())
        event = Event.objects.filter(name='MyTest01').first()

        url = reverse('event_create_sponsor_category', kwargs={'pk': event.pk})
        data = {
            'name': 'Gold',
            'amount': '10000'
        }
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url, data)
        expected_url = reverse('event_detail', kwargs={'pk': event.pk})
        self.assertRedirects(response, expected_url)
        self.assertContainsMessage(response, DUPLICATED_SPONSOR_CATEGORY_MESSAGE)

    def test_cant_create_sponsor_category_not_event_organizer(self):
        set_current_user(User.objects.filter(username='organizer01').first())
        event = Event.objects.filter(name='MyTest02').first()
        url = reverse('event_create_sponsor_category', kwargs={'pk': event.pk})
        data = {
            'name': 'Oro',
            'amount': '10000'
        }
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url, data)
        self.assertContainsMessage(response, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
        self.assertFalse(SponsorCategory.objects.filter(name='Oro').exists())

    def test_create_sponsor_category_by_event_organizer(self):
        set_current_user(User.objects.filter(username='organizer01').first())
        event = Event.objects.filter(name='MyTest01').first()

        url = reverse('event_create_sponsor_category', kwargs={'pk': event.pk})
        data = {
            'name': 'Oro',
            'amount': '50000'
        }
        self.client.login(username='organizer01', password='organizer01')
        self.client.post(url, data)

        self.assertTrue(SponsorCategory.objects.filter(name='Oro').exists())

    def test_event_change_not_updating_name_and_commission(self):
        event = Event.objects.filter(name='MyTest01').first()
        old_name = event.name
        old_commission = event.commission

        url = reverse('event_change', kwargs={'pk': event.pk})
        self.client.login(username='organizer01', password='organizer01')
        data = {
            'name': 'noChange',
            'commission': '300',
            'place': 'Villa adelina'
        }
        response = self.client.post(url, data)
        expected_url = reverse('event_detail', kwargs={'pk': event.pk})
        self.assertRedirects(response, expected_url)
        event.refresh_from_db()
        self.assertEqual(event.name, old_name)
        self.assertEqual(event.commission, old_commission)
        self.assertEqual(event.place, 'Villa adelina')


class SponsorViewsTest(TestCase, CustomAssertMethods):
    def setUp(self):
        super().setUp()
        create_organizer_set(auto_create_user_set=True)

    def test_organizer_cant_set_sponsors_enabled(self):
        sponsor = Sponsor.objects.create(**sponsor_data)
        url = reverse('sponsor_set_enabled', kwargs={'pk': sponsor.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url)
        self.assertForbidden(response)

    def test_can_set_sponsors_enabled_with_perms(self):
        sponsor = Sponsor.objects.create(**sponsor_data)
        url = reverse('sponsor_set_enabled', kwargs={'pk': sponsor.pk})
        self.client.login(username='superOrganizer01', password='superOrganizer01')
        response = self.client.post(url)
        redirect_to_login_url = reverse('sponsor_detail', kwargs={'pk': sponsor.pk})
        self.assertRedirects(response, redirect_to_login_url)

    def test_organizer_can_create_sponsor(self):
        sponsors_count = Sponsor.objects.all().count()
        url = reverse('sponsor_create')
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url, data=sponsor_data)
        self.assertEqual(Sponsor.objects.all().count(), sponsors_count + 1)
        self.assertEqual(response.status_code, 302)


class SponsoringViewsTest(TestCase, CustomAssertMethods):
    def setUp(self):
        create_organizer_set(auto_create_user_set=True)
        user = User.objects.first()
        create_event_set(user)
        associate_events_organizers()

    def test_cant_get_sponsor_create_form_without_sponsors(self):
        event = Event.objects.filter(name='MyTest01').first()
        url = reverse('sponsoring_create', kwargs={'event_pk': event.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.get(url)
        self.assertContainsMessage(response, MUST_EXISTS_SPONSOR_MESSAGE)
        redirect_url = reverse('sponsoring_list', kwargs={'event_pk': event.pk})
        self.assertRedirects(response, redirect_url)

    def test_cant_get_sponsor_create_form_without_sponsor_category(self):
        create_sponsors_set()
        event = Event.objects.filter(name='MyTest02').first()
        url = reverse('sponsoring_create', kwargs={'event_pk': event.pk})
        self.client.login(username='organizer02', password='organizer02')
        response = self.client.get(url)
        self.assertContainsMessage(response, MUST_EXISTS_SPONSOR_CATEGORY_MESSAGE)
        redirect_url = reverse('sponsoring_list', kwargs={'event_pk': event.pk})
        self.assertRedirects(response, redirect_url)

    def test_cant_get_sponsor_create_form_if_not_event_organizer(self):
        create_sponsors_set()
        event = Event.objects.filter(name='MyTest02').first()
        SponsorCategory.objects.create(name='Silver', amount=1000, event=event)

        url = reverse('sponsoring_create', kwargs={'event_pk': event.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.get(url)
        self.assertContainsMessage(response, MUST_BE_EVENT_ORGANIZAER_MESSAGE)
        redirect_url = reverse('event_list')
        self.assertRedirects(response, redirect_url)

    def test_organizer_can_create_sponsoring(self):
        create_sponsors_set()
        event = Event.objects.filter(name='MyTest01').first()
        url = reverse('sponsoring_create', kwargs={'event_pk': event.pk})
        self.client.login(username='organizer01', password='organizer01')
        sponsor_category = SponsorCategory.objects.filter(event=event).first()
        data = {
            'comments': ''
        }
        sponsor = Sponsor.objects.filter(enabled=True).first()
        data['sponsorcategory'] = sponsor_category.pk
        data['sponsor'] = sponsor.pk
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

    def test_sponsoring_create_form_prefiltered(self):
        create_sponsors_set()
        event = Event.objects.filter(name='MyTest01').first()
        event02 = Event.objects.filter(name='MyTest02').first()
        sponsor_category = SponsorCategory.objects.create(
            name='TEst',
            amount=1000,
            event=event02
        )

        url = reverse('sponsoring_create', kwargs={'event_pk': event.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.get(url)
        sponsor_form_field = response.context['form'].fields['sponsor']
        sponsor_category_form_field = response.context['form'].fields['sponsorcategory']
        not_enabled_sponsor = Sponsor.objects.filter(enabled=False).first()
        enabled_sponsor = Sponsor.objects.filter(enabled=True).first()
        self.assertNotIn(not_enabled_sponsor, sponsor_form_field._get_queryset())
        self.assertIn(enabled_sponsor, sponsor_form_field._get_queryset())
        self.assertNotIn(sponsor_category, sponsor_category_form_field._get_queryset())

    def test_cant_access_sponsoring_detail_if_not_event_organizer(self):
        create_sponsoring_set(auto_create_sponsors_set=True)
        event = Event.objects.filter(name='MyTest01').first()
        sponsoring = Sponsoring.objects.filter(sponsorcategory__event=event).first()

        url = reverse('sponsoring_detail', kwargs={'pk': sponsoring.pk})
        self.client.login(username='organizer03', password='organizer03')
        response = self.client.get(url)
        self.assertContainsMessage(response, MUST_BE_EVENT_ORGANIZAER_MESSAGE)

    def test_cant_access_sponsoring_list_if_not_event_organizer(self):
        create_sponsoring_set(auto_create_sponsors_set=True)
        event = Event.objects.filter(name='MyTest01').first()

        url = reverse('sponsoring_list', kwargs={'event_pk': event.pk})
        self.client.login(username='organizer03', password='organizer03')
        response = self.client.get(url)
        self.assertContainsMessage(response, MUST_BE_EVENT_ORGANIZAER_MESSAGE)

    def test_organizer_cant_close_sponsoring(self):
        create_sponsoring_set(auto_create_sponsors_set=True)
        event = Event.objects.filter(name='MyTest01').first()
        sponsoring = Sponsoring.objects.filter(sponsorcategory__event=event).first()

        self.assertFalse(sponsoring.close)
        url = reverse('sponsoring_set_close', kwargs={'pk': sponsoring.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url)
        self.assertForbidden(response)

    def test_super_organizer_can_close_sponsoring(self):
        # Test 'close' state from 'unbilled'.
        create_sponsoring_set(auto_create_sponsors_set=True)
        event = Event.objects.filter(name='MyTest01').first()
        sponsoring = Sponsoring.objects.filter(sponsorcategory__event=event).first()
        self.assertEqual(sponsoring.state, SPONSOR_STATE_UNBILLED)
        url = reverse('sponsoring_set_close', kwargs={'pk': sponsoring.pk})
        self.client.login(username='superOrganizer01', password='superOrganizer01')
        response = self.client.post(url)

        redirect_url = reverse('sponsoring_detail', kwargs={'pk': sponsoring.pk})
        self.assertRedirects(response, redirect_url, target_status_code=302)
        self.assertContainsMessage(response, SPONSORING_SUCCESSFULLY_CLOSE_MESSAGE)

        sponsoring.refresh_from_db()
        self.assertEqual(sponsoring.state, SPONSOR_STATE_CLOSED)

    def test_organizer_cant_set_complete_payment(self):
        invoice = create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        url = reverse('invoice_set_complete_payment', kwargs={'pk': invoice.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url)
        self.assertForbidden(response)

    def test_super_organizer_can_set_complete_payment(self):
        invoice = create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        invoice.invoice_ok = True
        invoice.save()
        self.assertEqual(invoice.sponsoring.state, SPONSOR_STATE_CHECKED)
        url = reverse('invoice_set_complete_payment', kwargs={'pk': invoice.pk})
        self.client.login(username='superOrganizer01', password='superOrganizer01')
        response = self.client.post(url)

        redirect_url = reverse('sponsoring_detail', kwargs={'pk': invoice.sponsoring.pk})

        self.assertRedirects(response, redirect_url, target_status_code=302)
        self.assertContainsMessage(response, INVOICE_SET_COMPLETE_PAYMENT_MESSAGE)
        invoice.sponsoring.refresh_from_db()
        self.assertEqual(invoice.sponsoring.state, SPONSOR_STATE_COMPLETELY_PAID)

    def test_organizer_cant_set_partial_payment(self):
        invoice = create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        url = reverse('invoice_set_partial_payment', kwargs={'pk': invoice.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url)
        self.assertForbidden(response)

    def test_super_organizer_can_set_partial_payment(self):
        invoice = create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        invoice.invoice_ok = True
        invoice.save()
        self.assertEqual(invoice.sponsoring.state, SPONSOR_STATE_CHECKED)
        url = reverse('invoice_set_partial_payment', kwargs={'pk': invoice.pk})
        self.client.login(username='superOrganizer01', password='superOrganizer01')
        response = self.client.post(url)

        redirect_url = reverse('sponsoring_detail', kwargs={'pk': invoice.sponsoring.pk})

        self.assertRedirects(response, redirect_url, target_status_code=302)
        self.assertContainsMessage(response, INVOICE_SET_PARTIAL_PAYMENT_MESSAGE)
        invoice.sponsoring.refresh_from_db()
        self.assertEqual(invoice.sponsoring.state, SPONSOR_STATE_PARTIALLY_PAID)

    def test_sponsoring_state_to_invoiced_after_invoice_asscociation(self):
        create_sponsoring_set(auto_create_sponsors_set=True)
        event = Event.objects.filter(name='MyTest01').first()
        sponsoring = Sponsoring.objects.filter(sponsorcategory__event=event).first()
        self.assertEqual(sponsoring.state, SPONSOR_STATE_UNBILLED)
        create_sponsoring_invoice()
        sponsoring.refresh_from_db()
        self.assertEqual(sponsoring.state, SPONSOR_STATE_INVOICED)

    def test_organizer_cant_add_invoice(self):
        create_sponsoring_set(auto_create_sponsors_set=True)
        event = Event.objects.filter(name='MyTest01').first()
        sponsoring = Sponsoring.objects.filter(sponsorcategory__event=event).first()
        url = reverse('sponsoring_invoice_create', kwargs={'pk': sponsoring.pk})
        self.client.login(username='organizer01', password='organizer01')
        data = {
            'amount': '40000',
            'document': StringIO('test'),
        }
        response = self.client.post(url, data)
        self.assertForbidden(response)

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_super_user_can_add_invoice(self, mock_save):
        mock_save.return_value = 'invoice.pdf'
        create_sponsoring_set(auto_create_sponsors_set=True)
        event = Event.objects.filter(name='MyTest01').first()
        sponsoring = Sponsoring.objects.filter(sponsorcategory__event=event).first()
        url = reverse('sponsoring_invoice_create', kwargs={'pk': sponsoring.pk})
        self.client.login(username='administrator', password='administrator')
        data = {
            'amount': '40000',
            'document': StringIO('test'),
        }
        response = self.client.post(url, data)
        redirect_url = reverse('sponsoring_detail', kwargs={'pk': sponsoring.pk})
        self.assertRedirects(response, redirect_url)
        sponsoring.refresh_from_db()
        self.assertEqual(sponsoring.state, SPONSOR_STATE_INVOICED)

    def test_organizer_can_check_invoice(self):
        invoice = create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        self.assertEqual(invoice.sponsoring.state, SPONSOR_STATE_INVOICED)

        url = reverse('invoice_set_approved', kwargs={'pk': invoice.pk})
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url)

        redirect_url = reverse('sponsoring_detail', kwargs={'pk': invoice.sponsoring.pk})

        self.assertRedirects(response, redirect_url)
        self.assertContainsMessage(response, INVOICE_APPOVED_MESSAGE)
        invoice.sponsoring.refresh_from_db()
        self.assertEqual(invoice.sponsoring.state, SPONSOR_STATE_CHECKED)

    def test_organizer_can_add_invoice_affect(self):
        invoice = create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        invoice.invoice_ok = True
        invoice.save()

        url = reverse('sponsoring_invoice_affect_create', kwargs={'pk': invoice.pk})
        self.client.login(username='organizer01', password='organizer01')
        data = {
            'amount': '1000',
            'category': 'Pay',
            'document': StringIO('test'),
        }
        response = self.client.post(url, data)
        redirect_url = reverse('sponsoring_detail', kwargs={'pk': invoice.sponsoring.pk})
        self.assertRedirects(response, redirect_url)
        invoice.sponsoring.refresh_from_db()
        self.assertEqual(invoice.sponsoring.state, SPONSOR_STATE_CHECKED)

    def test_validate_correct_cuits(self):
        cuits_ok = ['20364360607', '20-36436060-7', '55000002126', '55-00000212-6']

        for cuit in cuits_ok:
            self.assertTrue(validate_cuit(cuit))

    def test_validate_incorrect_cuits(self):
        cuits_nok = ['12345678912', '12-34854949-1', '20_36436060_7',
                     '55*00000212*6', '2', 'ad-sdqerfsc-w']

        with self.assertRaises(ValidationError):
            for cuit in cuits_nok:
                validate_cuit(cuit)


class PendindTaskTest(TestCase, CustomAssertMethods):

    def setUp(self):
        create_organizer_set(auto_create_user_set=True)
        user = User.objects.first()
        create_event_set(user)
        associate_events_organizers()
        self.invoice = create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)

    def test_organizer_get_associate_events_not_include_close(self):
        organizer = Organizer.objects.get(user__username='organizer01')
        events = organizer.get_associate_events()
        event01 = Event.objects.filter(name='MyTest01').first()
        self.assertIn(event01, events)
        event01.close = True
        event01.save()
        events = organizer.get_associate_events()
        self.assertNotIn(event01, events)

    def test_not_approved_invoices(self):
        organizer = Organizer.objects.get(user__username='organizer01')
        invoices = _not_approved_invoices(organizer)
        self.assertIn(self.invoice, invoices)
        # After approve is not
        self.invoice.invoice_ok = True
        self.invoice.save()
        invoices = _not_approved_invoices(organizer)
        self.assertNotIn(self.invoice, invoices)

    def test_orgnizer_complete_data(self):
        organizer = Organizer.objects.get(user__username='organizer01')
        self.assertFalse(organizer.has_complete_personal_data())
        # True after complete first and last name
        organizer.first_name = "TestFirstName"
        organizer.last_name = "TestLastName"
        organizer.save()
        self.assertTrue(organizer.has_complete_personal_data())

    @patch('events.helpers.task._incomoplete_events', return_value=[])
    @patch('events.helpers.task._not_sponsor_category', return_value=[])
    @patch('events.helpers.task._not_approved_invoices', return_value=[])
    @patch('events.models.Organizer.has_complete_personal_data', return_value=True)
    @patch('events.models.Organizer.has_account_data', return_value=False)
    def test_calculate_organizer_tasks(
        self,
        organizer_has_account_data_function,
        organizer_has_complete_personal_data_function,
        not_approved_invoices_function,
        not_sponsor_category_function,
        incomplete_events_function
    ):
        # Some test that can be do it, are
        # The functions _incomoplete_events, _not_sponsor_category, _not_approved_invoices
        # organizer.has_complete_personal_data and has_account_data are called
        # incomplete_events_function.return_value = [Event.objects.filter(name='MyTest01').first()]
        organizer = Organizer.objects.get(user__username='organizer01')
        tasks = calculate_organizer_task(organizer.user)
        incomplete_events_function.assert_called_once_with(organizer)
        not_sponsor_category_function.assert_called_once_with(organizer, [])
        not_approved_invoices_function.assert_called_once_with(organizer)
        organizer_has_complete_personal_data_function.assert_called_once()
        organizer_has_account_data_function.assert_called_once()

        self.assertEqual(len(tasks), 1)

    @patch('events.helpers.task.not_enabled_sponsor_task_builder', return_value=test_task)
    def test_not_enabled_sponsors_called(self, not_enabled_sponsor_function):
        calculate_super_user_task()
        sponsors = Sponsor.objects.filter(enabled=False)

        for sponsor in sponsors:
            not_enabled_sponsor_function.assert_called_with(sponsor)

    @patch('events.helpers.task.unpayment_invoices_task_builder', return_value=test_task)
    def test_invoice_on_unpayment_invoice_task(self, unpayment_task_builder_function):
        self.invoice.invoice_ok = True
        self.invoice.save()
        create_invoice_affect_set(self.invoice)
        calculate_super_user_task()
        unpayment_task_builder_function.assert_called_once_with(self.invoice)

    @patch('events.helpers.task.unpayment_invoices_task_builder', return_value=test_task)
    @patch('events.helpers.task.invoices_to_complete_task_builder', return_value=test_task)
    def test_invoice_on_to_complete_invoice_task(
        self,
        invoices_to_complete_builder_function,
        unpayment_task_builder_function
    ):
        self.invoice.invoice_ok = True
        self.invoice.save()
        create_invoice_affect_set(self.invoice, total_amount=True)
        calculate_super_user_task()
        invoices_to_complete_builder_function.assert_called_once_with(self.invoice)
        self.assertFalse(unpayment_task_builder_function.called)

    @patch('events.helpers.task.provider_payment_unfinish_task_builder', return_value=test_task)
    def test_providerexpense_no_payment(self, provider_payment_unfinish_task_builder):
        expense = create_provider_expense()
        calculate_super_user_task()
        provider_payment_unfinish_task_builder.assert_called_with(expense)

    @patch('events.helpers.task.provider_payment_unfinish_task_builder', return_value=test_task)
    def test_providerexpense_paid(self, provider_payment_unfinish_task_builder):
        create_provider_expense(payment=Payment.objects.create(document='testdoc'))
        calculate_super_user_task()
        provider_payment_unfinish_task_builder.assert_not_called()

    @patch('events.helpers.task.provider_payment_unfinish_task_builder', return_value=test_task)
    def test_providerexpense_cancelled(self, provider_payment_unfinish_task_builder):
        create_provider_expense(cancelled_date=timezone.now())
        calculate_super_user_task()
        provider_payment_unfinish_task_builder.assert_not_called()


class ProviderViewsTest(TestCase, CustomAssertMethods):

    def setUp(self):
        create_organizer_set(auto_create_user_set=True)

    def test_can_create_provider_with_perms(self):
        perm = Permission.objects.get(
            content_type__app_label='events',
            codename='add_provider')
        user = User.objects.get(username='organizer01')
        user.user_permissions.add(perm)

        providers_count = Provider.objects.all().count()
        url = reverse('provider_create')
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url, data=provider_data)
        self.assertEqual(Provider.objects.all().count(), providers_count + 1)
        self.assertEqual(response.status_code, 302)

    def test_create_provider_forbidden_without_perms(self):
        url = reverse('provider_create')
        perm = Permission.objects.get(
            content_type__app_label='events',
            codename='add_provider')
        user = User.objects.get(username='organizer01')
        user.user_permissions.remove(perm)
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url, data=provider_data)
        self.assertForbidden(response)


class ProviderExpenseViewsTest(TestCase, CustomAssertMethods):

    def setUp(self):
        user = User.objects.first()
        create_organizer_set(auto_create_user_set=True)
        create_event_set(user)
        associate_events_organizers()
        create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        create_provider()

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_can_create_provider_expense_with_perms(self, mock_save):
        mock_save.return_value = 'invoice.pdf'
        perm = Permission.objects.get(
            content_type__app_label='events',
            codename='add_providerexpense')
        user = User.objects.get(username='organizer01')
        user.user_permissions.add(perm)

        provider_expense_count = ProviderExpense.objects.all().count()
        url = reverse(
            'provider_expense_create',
            kwargs={'event_pk': Event.objects.filter(name='MyTest01').first().pk}
        )

        provider_expense_data = {
            'provider': Provider.objects.first().pk,
            'amount': '1200',
            'invoice_type': 'A',
            'invoice_date': '12/01/2019',
            'invoice': StringIO('test'),
            'description': 'test'
        }
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url, data=provider_expense_data)
        self.assertEqual(ProviderExpense.objects.all().count(), provider_expense_count + 1)
        self.assertEqual(response.status_code, 302)

    def test_create_provider_expense_forbidden_without_perms(self):
        url = reverse(
            'provider_expense_create',
            kwargs={'event_pk': Event.objects.filter(name='MyTest01').first().pk}
        )
        perm = Permission.objects.get(
            content_type__app_label='events',
            codename='add_providerexpense')

        provider_expense_data = {
            'provider': Provider.objects.first().pk,
            'amount': '1200',
            'invoice_type': 'A',
            'invoice_date': '12/01/2019',
            'invoice': StringIO('test'),
            'description': 'test'
        }
        user = User.objects.get(username='organizer01')
        user.user_permissions.remove(perm)
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url, data=provider_expense_data)
        self.assertForbidden(response)


class ProviderExpenseSwitchStateTest(TestCase, CustomAssertMethods):

    def setUp(self):
        create_organizer_set(auto_create_user_set=True)
        user = User.objects.first()
        create_event_set(user)
        associate_events_organizers()
        create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        create_provider()
        create_provider_expense()

    def test_provider_expense_switch_state(self):
        expense = ProviderExpense.objects.first()
        url = reverse(
            'provider_expense_switch_state',
            kwargs={'pk': expense.pk}
        )
        perm = Permission.objects.get(
            content_type__app_label='events',
            codename='change_providerexpense')

        user = User.objects.get(username='organizer01')
        user.user_permissions.add(perm)
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url)

        # View redirect.
        self.assertEqual(response.status_code, 302)

        # Switch to cancelled
        expense.refresh_from_db()
        self.assertEqual(expense.is_cancelled, True)

        # Switch back to not cancelled
        response = self.client.post(url)
        expense.refresh_from_db()
        self.assertEqual(expense.is_cancelled, False)


class OrganizerRefundSwitchStateTest(TestCase, CustomAssertMethods):
    def setUp(self):
        create_organizer_set(auto_create_user_set=True)
        user = User.objects.first()
        create_event_set(user)
        associate_events_organizers()
        create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        create_provider()
        create_organizer_refund()

    def test_organizer_refund_switch_state(self):
        refund = OrganizerRefund.objects.first()
        url = reverse(
            'organizer_refund_switch_state',
            kwargs={'pk': refund.pk}
        )
        perm = Permission.objects.get(
            content_type__app_label='events',
            codename='change_organizerrefund')

        user = User.objects.get(username='organizer01')
        user.user_permissions.add(perm)
        self.client.login(username='organizer01', password='organizer01')
        response = self.client.post(url)

        # View redirect.
        self.assertEqual(response.status_code, 302)

        # Switch to cancelled
        refund.refresh_from_db()
        self.assertEqual(refund.is_cancelled, True)

        # Switch back to not cancelled
        response = self.client.post(url)
        refund.refresh_from_db()
        self.assertEqual(refund.is_cancelled, False)


class PendindSponsoringTest(TestCase, CustomAssertMethods):

    def setUp(self):
        create_organizer_set(auto_create_user_set=True)
        self.user = User.objects.first()
        create_event_set(self.user)
        associate_events_organizers()
        self.invoice = create_sponsoring_invoice(auto_create_sponsoring_and_sponsor=True)
        create_invoice_affect_set(self.invoice, total_amount=False)
        self.invoice.invoice_ok = True
        self.invoice.partial_payment = True
        self.invoice.save()

    def test_pending_sponsoring_method(self):
        sponsoring = Sponsoring.objects.first()
        sponsoring_namedtuple = pending_sponsoring(sponsoring)
        self.assertIsInstance(sponsoring_namedtuple, PendingSponsoring)

    def test_calculate_all_sponsoring_pending(self):
        sponsoring = calculate_sponsoring_pending()
        self.assertEqual(len(sponsoring), 1)

    def test_calculate_all_sponsoring_pending_by_organizer(self):
        user = User.objects.get(username="organizer01")
        sponsoring = calculate_sponsoring_pending(user)
        self.assertEqual(len(sponsoring), 1)
        user = User.objects.get(username="organizer03")
        sponsoring = calculate_sponsoring_pending(user)
        self.assertEqual(len(sponsoring), 0)
