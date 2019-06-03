from django.contrib.messages import get_messages
from django.utils.translation import ugettext_lazy as _

from unittest import TestCase


def get_response_wsgi_messages(response):
    storage = get_messages(response.wsgi_request)
    return [message.message for message in storage]


class CustomAssertMethods(TestCase):

    def assertContainsMessage(self, response, message_text):
        messages = get_response_wsgi_messages(response)
        compare_messages = ((message == message_text) for message in messages)
        self.assertTrue(any(compare_messages),
                        _(f"Mensaje: '{message_text}' no encontrado en la lista de mensajes."))
