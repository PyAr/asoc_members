import shutil
import tempfile
import os
import os.path

from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage

from events.models import Expense
from utils import gdrive

# https://drive.google.com/drive/u/0/folders/1Kvfmz1eTNd9y2ZAqosaN3Cn2ydUKjtN_
BASE_FOLDER = '1Kvfmz1eTNd9y2ZAqosaN3Cn2ydUKjtN_'

# folder names in function of invoice type
FOLDER_TYPE_NAMES = {
    Expense.INVOICE_TYPE_A: 'Facturas A',
    Expense.INVOICE_TYPE_B: 'Facturas B',
    Expense.INVOICE_TYPE_C: 'Facturas C',
    Expense.INVOICE_TYPE_TICKET: 'Tickets',
    Expense.INVOICE_TYPE_OTHER: 'Otros',
}

# to avoid messing with gdrive every time
DIR_CACHE = {}


def ensure_directory(explorer, parent_id, dirname):
    """Ensure 'dirname' directory is present in 'parent'."""
    cache_key = (parent_id, dirname)
    if cache_key in DIR_CACHE:
        return DIR_CACHE[cache_key]

    for folder in explorer.list_folder(parent_id):
        if folder['name'] == dirname:
            folder_id = folder['id']
            break
    else:
        print("Creating folder {!r} in parent {}".format(dirname, parent_id))
        folder_id = explorer.create_folder(dirname, parent_id)
    DIR_CACHE[cache_key] = folder_id
    return folder_id


class Command(BaseCommand):
    help = "Upload those invoices type A to gdrive"

    def add_arguments(self, parser):
        parser.add_argument('year', type=int)
        parser.add_argument('month', type=int)

    def handle(self, *args, **options):
        year = int(options['year'])
        month = int(options['month'])

        expenses = Expense.objects.filter(
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
            dest_foldername_ym = exp.invoice_date.strftime("%Y%m")
            dest_foldername_inv_type = FOLDER_TYPE_NAMES[exp.invoice_type]
            print("Processing", repr(dest_filename))

            # download the invoice content to a local temp file (flush at the end so all content is
            # available externally, and only after using it close it, as it will then removed)
            local_temp_fh = tempfile.NamedTemporaryFile(mode='wb')
            remote_fh = default_storage.open(exp.invoice.name)
            shutil.copyfileobj(remote_fh, local_temp_fh)
            local_temp_fh.flush()

            # upload to google drive
            explorer = gdrive.Explorer()

            # ensure both dirs are present
            parent_id = ensure_directory(explorer, BASE_FOLDER, dest_foldername_ym)
            folder_id = ensure_directory(explorer, parent_id, dest_foldername_inv_type)

            # upload
            explorer.upload(local_temp_fh.name, folder_id, filename=dest_filename)
            local_temp_fh.close()
