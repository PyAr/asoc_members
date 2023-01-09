import shutil
import tempfile
import os
import os.path

from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.utils import timezone

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
FILES_CACHE = {}


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


def get_files(explorer, folder_id):
    """Get files info for a specific folder, cached."""
    try:
        files = FILES_CACHE[folder_id]
    except KeyError:
        files = {f['name']: f for f in explorer.list_folder(folder_id)}
        FILES_CACHE[folder_id] = files
    return files


class Command(BaseCommand):
    help = "Upload those invoices type A to gdrive"

    def add_arguments(self, parser):
        parser.add_argument('yearmonth', type=str, nargs='?')

    def handle(self, *args, **options):
        yearmonth = options['yearmonth']
        if yearmonth is None:
            # by default is "last month"
            now = timezone.now()
            year = now.year
            month = now.month - 1
            if month <= 0:
                year -= 1
                month = 12
        else:
            if len(yearmonth) != 6 or not yearmonth.isdigit():
                print("USAGE: upload_gdrive_invoices.py [YYYYMM]")
                exit()
            year = int(yearmonth[:4])
            month = int(yearmonth[4:])

        # we filter on the date the invoice was *uploaded* to the system, otherwise we'd miss
        # those ones that are created too late, which is not rare for refunds
        print("Filtering expenses for year={!r} month={!r}".format(year, month))
        expenses = Expense.objects.filter(created__year=year, created__month=month).all()
        print("Found {} expenses".format(len(expenses)))

        explorer = gdrive.Explorer()

        for exp in expenses:
            # ensure needed parent directory is present in google drive
            yearmonth_foldername = "{}{:02d}".format(exp.invoice_date.year, exp.invoice_date.month)
            base_folder_id = ensure_directory(explorer, BASE_FOLDER, yearmonth_foldername)

            # build useful vars for later
            orig_name = os.path.basename(exp.invoice.name)
            extension = orig_name.rsplit('.')[-1].lower()
            dest_filename = "{:%Y%m%d} - {}: {} [${}] ({}).{}".format(
                exp.invoice_date, exp.event.name, exp.description,
                exp.amount, orig_name, extension)
            dest_foldername_inv_type = FOLDER_TYPE_NAMES[exp.invoice_type]
            print("Processing", repr(dest_filename))

            # ensure dir in google drive, see if file is already there
            folder_id = ensure_directory(explorer, base_folder_id, dest_foldername_inv_type)
            old_files = get_files(explorer, folder_id)
            if dest_filename in old_files:
                old_info = old_files[dest_filename]
                if int(old_info['size']) == default_storage.size(exp.invoice.name):
                    print("    ignoring, already updated")
                    continue
                print("    different size, uploading again")

            # download the invoice content to a local temp file (flush at the end so all content is
            # available externally, and only after using it close it, as it will then removed)
            local_temp_fh = tempfile.NamedTemporaryFile(mode='wb')
            remote_fh = default_storage.open(exp.invoice.name)
            shutil.copyfileobj(remote_fh, local_temp_fh)
            local_temp_fh.flush()

            # upload
            explorer.upload(local_temp_fh.name, folder_id, filename=dest_filename)
            local_temp_fh.close()
            print("    uploaded")
