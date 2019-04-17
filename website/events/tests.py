from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

def create_user_set():
    """Create a organizer and superuser users."""
    organizer = User.objects.create_user(username="organizer", email="test@test.com", password="organizer")
    super_user = User.objects.create_superuser(
        username="administrator", 
        email="admin@test.com", 
        password="administrator"
        )


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
        self.client.login(username='organizer', password='organizer')

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