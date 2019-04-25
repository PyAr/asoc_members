from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core import mail
from django.forms import modelform_factory, modelformset_factory
from django.test import TestCase, RequestFactory
from django.urls import reverse

from events.admin import EventAdmin
from events.models import Event, Organizer, EventOrganizer

User = get_user_model()
class MockSuperUser:
    def has_perm(self, perm):
        return True

def create_user_set():
    """Create a organizer and superuser users."""
    User.objects.create_user(username="organizer01", email="test01@test.com", password="organizer01")
    User.objects.create_user(username="organizer02", email="test02@test.com", password="organizer02")
    User.objects.create_superuser(
        username="administrator", 
        email="admin@test.com", 
        password="administrator"
        )

def create_event_set():
    """Create Events to test."""
    Event.objects.create(name='MyTest01', commission=20)
    Event.objects.create(name='MyTest02', commission=10)

def instantiate_formset(formset_class, data, instance=None, initial=None):
    prefix = formset_class().prefix
    formset_data = {}
    for i, form_data in enumerate(data):
        for name, value in form_data.items():
            if isinstance(value, list):
                for j, inner in enumerate(value):
                    formset_data['{}-{}-{}_{}'.format(prefix, i, name, j)] = inner
            else:
                formset_data['{}-{}-{}'.format(prefix, i, name)] = value
    formset_data['{}-TOTAL_FORMS'.format(prefix)] = len(data)
    formset_data['{}-INITIAL_FORMS'.format(prefix)] = 0

    if instance:
        return formset_class(formset_data, instance=instance, initial=initial)
    else:
        return formset_class(formset_data, initial=initial)

class EmailTest(TestCase):
    def setUp(self):
        create_user_set()

    def test_send_email_after_register_organizer(self):
        # Login client with super user
        self.client.login(username='administrator', password='administrator')

        # Send request
        data = {
            'username':'juanito',
            'email':'new_organizer@pyar.com',
        }
        response = self.client.post(reverse('organizer_signup'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        #TODO: use template here
        self.assertEqual(mail.outbox[0].subject, 'PyAr eventos alta organizador')



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
        #TODO: use correct perm, and not superuser
        # Login client with super user
        self.client.login(username='administrator', password='administrator')

        response = self.client.get(reverse('organizer_signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'organizer_signup.html')


class EventAdminTest(TestCase):
    def setUp(self):
        create_user_set()
        create_event_set()

        site = AdminSite()
        self.admin = EventAdmin(Event, site)
        Organizer.objects.bulk_create([
            Organizer(user=User.objects.get(username="organizer01"), first_name="Organizer01"),
            Organizer(user=User.objects.get(username="organizer02"), first_name="Organizer02")
        ])

    """def test_on_organizer_associate_to_event_call_mail_function(self):
        url = reverse('admin:events_event_change', kwargs={'object_id': 2})
        
        request_factory = RequestFactory()
        request = request_factory.get(url)
        request.user = MockSuperUser()

        event = Event.objects.filter(name='MyTest01').first()
        event_form = modelform_factory(Event, fields=['name', 'commission', 'id'])
        event_form_instance = event_form({'name':event.name, 'commission':event.commission}, instance=event)
        
        event_form_instance.is_valid()

        organizer = Organizer.objects.filter(first_name="Organizer01").first()
        event_organizer = EventOrganizer(event=event, organizer=organizer)
        event_organizer_form = modelform_factory(EventOrganizer, fields=['event', 'organizer'])
        event_organizer_form_instance = event_organizer_form({'event':event, 'organizer':organizer}, instance=event_organizer)
        event_organizer_form_instance.is_valid()

        event_organizer_formset = modelformset_factory(EventOrganizer, fields=['event', 'organizer'])
        #event_organizer_formset_instance = instantiate_formset(event_organizer_formset,[{
        #    'event':event,
        #    'organizer': organizer
        #}])
        #event_organizer_formset_instance.is_valid()
        event_organizer_formset_instance = event_organizer_formset([event_organizer_form_instance])
        #event_organizer_formset_instance.forms = 
        event_organizer_formset_instance.is_valid()
        

        self.admin.save_formset(
            request, 
            event_form_instance, 
            event_organizer_formset_instance, 
            True
            )
        self.assertEqual(1,1)"""