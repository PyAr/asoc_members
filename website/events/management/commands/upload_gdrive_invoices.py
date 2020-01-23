import shutil
import tempfile
import os
import os.path

from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage

from events.models import Expense
from website.utils import gdrive

# https://drive.google.com/drive/u/0/folders/1Kvfmz1eTNd9y2ZAqosaN3Cn2ydUKjtN_
BASE_FOLDER = '1Kvfmz1eTNd9y2ZAqosaN3Cn2ydUKjtN_'


class Command(BaseCommand):
    help = "Upload those invoices type A to gdrive"

    def add_arguments(self, parser):
        parser.add_argument('year', type=int)
        parser.add_argument('month', type=int)

    def handle(self, *args, **options):
        year = int(options['year'])
        month = int(options['month'])

        expenses = Expense.objects.filter(
            invoice_type=Expense.INVOICE_TYPE_A,
            invoice_date__year=year,
            invoice_date__month=month,
        ).all()
        print("Found {} expenses".format(len(expenses)))

        for exp in expenses:
            # build useful vars for later
            orig_name = os.path.basename(exp.invoice.name)
            extension = orig_name.rsplit('.')[-1].lower()
            dest_filename = "{:%Y%m%d} - {}: {} [${}] ({}).{}".format(
                exp.invoice_date, exp.event.name, exp.description,
                exp.amount, orig_name, extension)
            dest_foldername = exp.invoice_date.strftime("%Y%m")
            print("Processing", repr(dest_filename))

            # download the invoice content to a local temp file (flush at the end so all content is
            # available externally, and only after using it close it, as it will then removed)
            local_temp_fh = tempfile.NamedTemporaryFile(mode='wb')
            remote_fh = default_storage.open(exp.invoice.name)
            shutil.copyfileobj(remote_fh, local_temp_fh)
            local_temp_fh.flush()

            # upload to google drive
            explorer = gdrive.Explorer()

            # get the id of the month folder (or create it)
            for folder in explorer.list_folder(BASE_FOLDER):
                if folder['name'] == dest_foldername:
                    folder_id = folder['id']
                    break
            else:
                folder_id = explorer.create_folder(dest_foldername, BASE_FOLDER)

            explorer.upload(local_temp_fh.name, folder_id, filename=dest_filename)
            local_temp_fh.close()
