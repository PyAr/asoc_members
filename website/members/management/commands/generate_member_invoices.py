import datetime
import os

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.db.models import Max

from members import logic
from members.models import Quota, Person, Payment, Member, PaymentStrategy

from utils import gdrive, afip

INVOICES_FROM = '2018-08-01 00:00+03'
GMTminus3 = datetime.timezone(datetime.timedelta(hours=-3))

# mail stuff
MAIL_SUBJECT = "Factura por pago de cuota(s) a la Asociación Civil Python Argentina"
MAIL_TEXT = """\
Hola!

Adjunta va la factura por el pago hecho en fecha {payment_date:%Y-%m-%d}.

¡Gracias! Saludos,

--
.   Lalita
.
Asociación Civil Python Argentina
http://ac.python.org.ar/

(claro, este mail es automático, soy une bot, pero contestá el mail sin problemas que
le va a llegar al humane correspondiente)
"""
PDF_MIMETYPE = 'application/pdf'


def _send_mail(payment_date, recipient, attach_path):
    text = MAIL_TEXT.format(payment_date=payment_date)
    mail = EmailMessage(MAIL_SUBJECT, text, settings.EMAIL_FROM, [recipient])

    filename = os.path.basename(attach_path)
    with open(attach_path, "rb") as fh:
        attach_content = fh.read()
    mail.attach(filename, attach_content, PDF_MIMETYPE)
    mail.send()


class Command(BaseCommand):
    help = "Generate the missing invoices"

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, nargs='?', default=1)
        parser.add_argument(
            '--invoice-date', type=str, nargs='?', help="Invoice date (%Y-%m-%d), forces limit=1")

    def handle(self, *args, **options):
        limit = options['limit']
        invoice_date = options['invoice_date']
        if invoice_date is None:
            invoice_date = datetime.date.today()
        else:
            invoice_date = datetime.datetime.strptime(invoice_date, "%Y-%m-%d").date()
            limit = 1
            print("Forcing invoice date to {} (also limit=1)".format(invoice_date))
        records = []

        # check AFIP
        afip.verify_service(settings.AFIP['selling_point'])

        # get the greatest invoice number used (once, will keep updated later)
        _max_invoice_number_query = Payment.objects.aggregate(Max('invoice_number'))
        max_invoice_number = _max_invoice_number_query['invoice_number__max']
        print("Found max invoice number {}".format(max_invoice_number))

        # get payments after we started automatically that still have no invoice generated
        payments_per_invoice = {}
        persons_per_invoice = {}
        payments = (
            Payment.objects.filter(timestamp__gte=INVOICES_FROM, invoice_ok=False)
            .exclude(strategy__platform=PaymentStrategy.CREDIT)
            .order_by('timestamp', 'pk').all()
        )
        print("Found {} payments to process".format(len(payments)))
        if len(payments) > limit:
            payments = payments[:limit]
            print("    truncating to {}".format(limit))

        for payment in payments:
            print("Processing payment", payment)
            record = {
                'invoice_date': invoice_date,
            }

            # get the related member (if None, or multiple, still not supported!)
            _members = Member.objects.filter(patron=payment.strategy.patron).all()
            assert len(_members) == 1, "multiple or no members for the patron is not supported"
            member = _members[0]

            # only process payments for normal members (benefactor members get invoices done
            # by hand)
            person = member.entity
            if isinstance(person, Person):
                print("    person found", person)
            else:
                print("    IGNORING payment, member {} is not a person: {}".format(member, person))
                continue

            # if payment still doesn't have a number, add one to latest and save;
            # in any case, use it
            if not payment.invoice_number:
                max_invoice_number += 1
                payment.invoice_number = max_invoice_number
                payment.invoice_spoint = settings.AFIP['selling_point']
                payment.save()
                print("    using new invoice number", payment.invoice_number)
            else:
                print("    using already stored invoice number", payment.invoice_number)
            assert payment.invoice_spoint == settings.AFIP['selling_point']
            payments_per_invoice[payment.invoice_number] = payment
            record['invoice'] = payment.invoice_number

            # we bill one item, for the whole amount: "3 quotas for $300", instead of billing
            # 3 x "1 quota for $100", which would be problematic if the paid amount is
            # not exactly 300
            record['amount'] = payment.amount
            record['quantity'] = 1

            # get all billing data from the person
            persons_per_invoice[payment.invoice_number] = person
            record['dni'] = person.document_number
            record['fullname'] = person.full_name
            record['address'] = person.street_address
            record['city'] = person.city
            record['zip_code'] = person.zip_code
            record['province'] = person.province
            tstamp_argentina = payment.timestamp.astimezone(GMTminus3)
            record['payment_comment'] = "Pago via {} ({:%Y-%m-%d %H:%M})".format(
                payment.strategy.platform_name, tstamp_argentina)

            # get quotas for the payment; we don't show the period in the description
            # as there's a specific field for that
            quotas = list(Quota.objects.filter(payment=payment).order_by('year', 'month').all())
            assert quotas
            if len(quotas) == 1:
                description = "1 cuota social"
            else:
                description = "{} cuotas sociales".format(len(quotas))
            record['description'] = description

            from_quota = quotas[0]
            from_day = datetime.date(from_quota.year, from_quota.month, 1)
            to_quota = quotas[-1]
            ny, nm = logic.increment_year_month(to_quota.year, to_quota.month)
            to_day = datetime.date(ny, nm, 1) - datetime.timedelta(days=1)
            record['service_date_from'] = from_day.strftime("%Y%m%d")
            record['service_date_to'] = to_day.strftime("%Y%m%d")
            print("    found {} quota(s) ({} - {})".format(
                len(quotas), record['service_date_from'], record['service_date_to']))
            records.append(record)

        if not records:
            print("No processable records found.")
            return

        # convert the stored records to proper invoices and call AFIP
        invoices = []
        for rec in records:
            invoice = afip.MemberInvoice(
                document_number=rec['dni'], fullname=rec['fullname'],
                address=rec['address'], city=rec['city'], zip_code=rec['zip_code'],
                province=rec['province'], invoice_date=rec['invoice_date'],
                invoice_number=rec['invoice'],
                service_date_from=rec['service_date_from'],
                service_date_to=rec['service_date_to'],
                selling_point=settings.AFIP['selling_point'])
            description = "{}\n{}".format(rec['description'], rec['payment_comment'])
            invoice.add_item(
                description=description, quantity=rec['quantity'], amount=rec['amount'])
            invoices.append(invoice)
        print("Invoices generated, calling AFIP...")
        try:
            results = afip.process_invoices(invoices, settings.AFIP['selling_point'])
        except Exception:
            print("    PROBLEMS processing invoices", invoices)
            raise
        print("AFIP interaction ended correctly")

        # save the results for the generated ok invoices
        storing_info = []
        for invoice_number, result in sorted(results.items()):
            print("Checking invoice {} results {}".format(invoice_number, result))
            if not result['invoice_ok']:
                print("    WARNING: invoice NOT authorized ok")
                continue

            payment = payments_per_invoice[invoice_number]
            payment.invoice_ok = True
            payment.save()

            storing_info.append((result['pdf_path'], invoice_number, payment))
            print("    ok")

        # at this point the AFIP cycle is closed: if AFIP approved the invoice it's flagged as
        # ok in our DB, the worst thing that can happen now is failing to storing the PDF in
        # gdrive or sending it by mail
        for pdf_path, invoice_number, payment in storing_info:
            print("Post-processing invoice {} at {}".format(invoice_number, pdf_path))
            storing_ok = True

            # upload the invoice to google drive
            try:
                gdrive.upload_invoice(pdf_path, invoice_date)
            except Exception as err:
                storing_ok = False
                print("    failed uploading to gdrive:", repr(err))
            else:
                print("    uploaded to gdrive OK")

            # send the invoice by mail
            try:
                person = persons_per_invoice[invoice_number]
                _send_mail(payment.timestamp, person.email, pdf_path)
            except Exception as err:
                storing_ok = False
                print("    failed sending by mail:", repr(err))
            else:
                print("    sent by mail OK")

            if storing_ok:
                # invoice uploaded to gdrive and sent ok, don't need it here anymore
                os.remove(pdf_path)
            else:
                print("    ERROR! Keeping invoice PDF")
