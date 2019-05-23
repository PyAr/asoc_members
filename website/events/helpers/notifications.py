from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string


class EmailNotification():
    EMAIL_TEMPLATES = {
        'organizer_associated_to_event': 'mails/organizer_associated_to_event_email.html'
    }
    EMAIL_SUBJECTS = {
        'organizer_associated_to_event': 'mails/organizer_associated_to_event_subject.txt'
    }

    def send_organizer_associated_to_event(self, event, organizers, context):
        """Send email notifiying new organizer user association with event.
        Args:
            event: Event where organizers are associated
            organizers: List of organizers to notify association
            context: Context to compleate at less 'domain' and 'protocol'
        """
        template = self.EMAIL_TEMPLATES.get('organizer_associated_to_event')
        subject = render_to_string(self.EMAIL_SUBJECTS.get('organizer_associated_to_event'))
        messages = []
        for organizer in organizers:
            context['event'] = event
            context['organizer'] = organizer
            body = render_to_string(template, context)
            recipients = organizer.user.email
            message = self._contruct_message(subject, body, recipients)
            messages.append(message)

        connection = mail.get_connection()
        # Send the two emails in a single call -
        connection.send_messages(messages)
        # The connection was already open so send_messages() doesn't close it.
        # We need to manually close the connection.
        connection.close()

    def _contruct_message(self, subject, body, recipients):
        return mail.EmailMessage(
            subject, body, settings.MAIL_FROM, [recipients],
            cc=[settings.MAIL_MANAGER], reply_to=[settings.MAIL_MANAGER])


email_notifier = EmailNotification()
