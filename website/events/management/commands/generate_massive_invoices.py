import datetime
import decimal
import os

from django.core.management.base import BaseCommand

from utils import gdrive, afip

# https://drive.google.com/drive/u/0/folders/1EJjXYrwYxfUaBdOiswlP-xvUBlqrkAHl
BASE_FOLDER = '1EJjXYrwYxfUaBdOiswlP-xvUBlqrkAHl'

# selling point for massive invoices
SELLING_POINT = 9


class Command(BaseCommand):
    help = "Generate massive quantity of invoices"

    def add_arguments(self, parser):
        parser.add_argument('quantity', type=int)
        parser.add_argument('starting_invoice_number', type=int)
        parser.add_argument('description', type=str)
        parser.add_argument('amount', type=decimal.Decimal)
        parser.add_argument('--force', action='store_true')

    def handle(self, *args, **options):
        quantity = options['quantity']
        starting_invoice_number = options['starting_invoice_number']
        description = options['description']
        amount = options['amount']
        force = options['force']

        # check AFIP
        last_verified = afip.verify_service(SELLING_POINT)
        if starting_invoice_number != last_verified + 1:
            print("Bad invoice number (given: {!r}, last authorized: {!r})".format(
                starting_invoice_number, last_verified))
            if force:
                print("Even so going on, per --force")
            else:
                print("Quitting")
                return

        records = []
        invoice_date = datetime.date.today()
        for invoice_idx in range(quantity):
            record = {
                'invoice_number': starting_invoice_number + invoice_idx,
                'amount': amount,
                'quantity': 1,
                'description': description,
            }
            records.append(record)

        # convert the records to proper invoices, call AFIP, and upload
        # PDF, all sequentially for better fail support
        for rec in records:
            invoice_number = rec['invoice_number']
            print("Processing invoice {}".format(invoice_number))

            invoice = afip.MassiveProductSellingInvoice(
                selling_point=SELLING_POINT,
                invoice_number=rec['invoice_number'],
                invoice_date=invoice_date)
            invoice.add_item(
                description=rec['description'], quantity=rec['quantity'], amount=rec['amount'])

            try:
                results = afip.process_invoices([invoice], SELLING_POINT)
            except Exception:
                print("PROBLEMS processing invoice", invoice)
                raise

            (result,) = results.values()  # only one invoice processed!
            if not result['invoice_ok']:
                print("    WARNING: invoice NOT authorized ok")
                continue

            # upload the invoice to google drive
            gdrive.upload_invoice(result['pdf_path'], invoice_date, base_folder=BASE_FOLDER)
            print("    uploaded to gdrive OK")

            # invoice uploaded to gdrive and sent ok, don't need it here anymore
            os.remove(result['pdf_path'])

        print("Done")
