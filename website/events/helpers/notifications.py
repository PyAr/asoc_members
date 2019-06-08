from django.contrib.auth import get_user_model
from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string

User = get_user_model()


class EmailNotification():
    EMAIL_TEMPLATES = {
        'organizer_associated_to_event': 'mails/organizer_associated_to_event_email.html',
        'sponsor_just_created': 'mails/sponsor_just_created_email.html'
    }
    EMAIL_SUBJECTS = {
        'organizer_associated_to_event': 'mails/organizer_associated_to_event_subject.txt',
        'sponsor_just_created': 'mails/sponsor_just_created_subject.txt'
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

    def send_new_sponsor_created(self, sponsor, created_by, context):
        """Send email notifiying new sponsor was created.
        Args:
            sponsor: Sponsor just created
            created_by: User whos create the sponsor
            context: Context to compleate at less 'domain' and 'protocol'
        """
        template = self.EMAIL_TEMPLATES.get('sponsor_just_created')
        subject = render_to_string(self.EMAIL_SUBJECTS.get('sponsor_just_created'))

        messages = []
        recipients = self._get_superusers_emails()
        for recipient in recipients:
            context['sponsor'] = sponsor
            context['user'] = created_by
            body = render_to_string(template, context)
            message = self._contruct_message(subject, body, recipient)
            messages.append(message)

        connection = mail.get_connection()
        # Send the two emails in a single call -
        connection.send_messages(messages)
        # The connection was already open so send_messages() doesn't close it.
        # We need to manually close the connection.
        connection.close()

    def _get_superusers_emails(self):
        recipients = []
        users = User.objects.filter(is_superuser=True).exclude(email__exact='')
        for user in users.all():
            recipients.append(user.email)
        return recipients

    def _contruct_message(self, subject, body, recipients):
        return mail.EmailMessage(subject, body, settings.EMAIL_FROM, [recipients])


email_notifier = EmailNotification()
