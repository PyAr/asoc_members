from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from django.core import mail
User = get_user_model()

class EmailTest(TestCase):
    def setUp(self):
        self.organizer_user = User.objects.create_user(username="organizer", email="test@test.com", password="organizer")
        self.super_user = User.objects.create_superuser(
            username="administrator", 
            email="admin@test.com", 
            password="administrator"
            )
            
    def tearDown(self):
        self.organizer_user.delete()
        self.super_user.delete()

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

    #TODO: move to another test suite
    def test_organizer_signup_redirects_without_perms(self):
        response = self.client.get(reverse('organizer_signup'))
        # View redirect.
        self.assertEqual(response.status_code, 302)
        
        # And redirect to login.
        redirect_to_login_url = reverse('login') + '?next=' + reverse('organizer_signup')
        self.assertEqual(response.url, redirect_to_login_url)
        