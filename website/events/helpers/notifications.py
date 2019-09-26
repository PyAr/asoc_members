from django.contrib.auth import get_user_model
from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string

User = get_user_model()


class EmailNotification():
    ORGANIZER_ASSOCIATED_TO_EVENT = 'organizer_associated_to_event'
    SPONSOR_JUST_CREATED = 'sponsor_just_created'
    INVOICE_JUST_CREATED = 'invoice_just_created'
    INVOICE_AFFECT_JUST_CREATED = 'invoice_affect_just_created'
    SPONSOR_JUST_ENABLED = 'sponsor_just_enabled'
    SPONSORING_JUST_CREATED = 'sponsoring_just_created'

    EXPENSE_JUST_CREATED = 'expense_just_created'
    PROVIDER_PAYMENT_JUST_CREATED = 'provider_payment_just_created'
    ORGANIZER_PAYMENT_JUST_CREATED = 'organizer_payment_just_created'

    def _get_email_template(self, email_type):
        # TODO: check that the type is one of the email_types
        return f'mails/{email_type}_email.html'

    def _get_email_subject(self, email_type):
        return f'mails/{email_type}_subject.txt'

    def send_organizer_associated_to_event(self, event, organizers, context):
        """Send email notifiying new organizer user association with event.
        Args:
            event: Event where organizers are associated
            organizers: List of organizers to notify association
            context: Context to compleate at less 'domain' and 'protocol'
        """
        email_type = self.ORGANIZER_ASSOCIATED_TO_EVENT
        template = self._get_email_template(email_type)
        subject = render_to_string(self._get_email_subject(email_type))
        messages = []
        context['event'] = event
        for organizer in organizers:
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
        email_type = self.SPONSOR_JUST_CREATED
        recipients = self._get_superusers_emails()
        context['sponsor'] = sponsor
        context['user'] = created_by

        self._send_emails(email_type, recipients, context)

    def send_new_invoice_created(self, invoice, context):
        """Send email notifiying new invoice was created.
        Args:
            invoice: Invoice just created
            context: Context to compleate at less 'domain' and 'protocol'
        """
        email_type = self.INVOICE_JUST_CREATED

        event = invoice.sponsoring.sponsorcategory.event
        recipients = self._get_event_organizers_emails(event)
        context['event'] = event
        context['invoice'] = invoice
        self._send_emails(email_type, recipients, context)

    def send_new_invoice_affect_created(self, invoice_affect, created_by, context):
        """Send email notifiying new invoice affect was created.
        Args:
            invoice_affect: InvoiceAffect just created
            created_by: User whos create the sponsor
            context: Context to compleate at less 'domain' and 'protocol'
        """
        email_type = self.INVOICE_AFFECT_JUST_CREATED

        recipients = self._get_superusers_emails()
        context['invoice_affect'] = invoice_affect
        context['user'] = created_by

        self._send_emails(email_type, recipients, context)

    def send_sponsor_enabled(self, sponsor, context):
        """Send email notifiying that a sponsor was enabled.
        Args:
            sponsor: Sponsor just enabled
            context: Context to compleate at less 'domain' and 'protocol'
        """
        email_type = self.SPONSOR_JUST_ENABLED
        if sponsor.created_by.email:
            recipients = [sponsor.created_by.email]
            context['sponsor'] = sponsor
            self._send_emails(email_type, recipients, context)

    def send_new_provider_payment_created(self, expense, context):
        """Send email notifiying that a sponsor was enabled.
        Args:
            expense: Expense that was paid
            context: Context to compleate at less 'domain' and 'protocol'
        """
        email_type = self.PROVIDER_PAYMENT_JUST_CREATED
        if expense.created_by.email:
            recipients = [expense.created_by.email]
            context['expense'] = expense
            self._send_emails(email_type, recipients, context)

    def send_new_organizer_payment_created(self, expenses, organizer, context):
        """Send email notifiying that a sponsor was enabled.
        Args:
            expenses: Expenses that were paid
            organizer: Organizer to whom payments correspond
            context: Context to compleate at less 'domain' and 'protocol'
        """
        email_type = self.ORGANIZER_PAYMENT_JUST_CREATED
        if organizer.email:
            recipients = [organizer.email]
            context['expenses'] = expenses
            self._send_emails(email_type, recipients, context)

    def send_new_sponsoring_created(self, sponsoring, created_by, context):
        """Send email notifiying new sponsor was created.
        Args:
            sponsoring: Sponsoring just created
            created_by: User whos create the sponsor
            context: Context to compleate at less 'domain' and 'protocol'
        """
        email_type = self.SPONSORING_JUST_CREATED

        recipients = self._get_superusers_emails()
        context['sponsoring'] = sponsoring
        context['user'] = created_by
        self._send_emails(email_type, recipients, context)

    def send_new_expense_created(self, expense, created_by, context):
        """Send email notifiying new expense was created.
        New Payment flow started
        Args:
            expense: Expense just created
            created_by: User whos create the sponsor
            context: Context to compleate at less 'domain' and 'protocol'
        """
        email_type = self.EXPENSE_JUST_CREATED

        recipients = self._get_superusers_emails()
        context['expense'] = expense
        context['user'] = created_by
        self._send_emails(email_type, recipients, context)

    def _get_superusers_emails(self):
        recipients = []
        users = User.objects.filter(is_superuser=True).exclude(email__exact='')
        for user in users.all():
            recipients.append(user.email)
        return recipients

    def _get_event_organizers_emails(self, event):
        recipients = []
        for organizer in event.organizers.all():
            recipients.append(organizer.user.email)
        return recipients

    def _contruct_message(self, subject, body, recipients):
        return mail.EmailMessage(subject, body, settings.EMAIL_FROM, [recipients])

    def _send_emails(self, email_type, recipients, context):
        """ Send the same email to all recipients.
        Args:
            email_type: One of the self constants.
            recipients: List of emails to send messages
            context: Context to compleate at less 'domain' and 'protocol'
        """
        template = self._get_email_template(email_type)
        subject = render_to_string(self._get_email_subject(email_type))
        body = render_to_string(template, context)

        messages = []
        for recipient in recipients:
            message = self._contruct_message(subject, body, recipient)
            messages.append(message)

        connection = mail.get_connection()
        # Send the two emails in a single call -
        connection.send_messages(messages)
        # The connection was already open so send_messages() doesn't close it.
        # We need to manually close the connection.
        connection.close()


email_notifier = EmailNotification()
