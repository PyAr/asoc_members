import os

import httplib2
from apiclient import discovery, http
from oauth2client.file import Storage

from django.conf import settings

SCOPE = 'https://www.googleapis.com/auth/drive'
APPLICATION_NAME = 'AutoFacturador'
# FIXME: move these to the confiG
# CREDENTIALS_FILE = "/tmp/autofacturador_credentials.json"

# FIXME: move this to the config
# "Factura Socies" https://drive.google.com/drive/u/1/folders/1V2z4ww1B1yNdkO0yxkah45FX7sZvt961
# BASE_GDRIVE_FOLDER = "1V2z4ww1B1yNdkO0yxkah45FX7sZvt961"


def get_credentials():
    """Get valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    store = Storage(settings.INVOICES_GDRIVE['credentials_filepath'])
    credentials = store.get()
    if not credentials or credentials.invalid:
        raise RuntimeError("Invalid Google Drive credentials! Call the guru")

        # NOTE: this must be run in a place with a browser to authenticate the credential
        # from oauth2client import client, tools
        # flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPE)
        # flow.user_agent = APPLICATION_NAME
        # credentials = tools.run_flow(flow, store)#, auth_flags)
        # print('Storing credentials to %s', CREDENTIALS_FILE)
    return credentials


class Explorer:
    def __init__(self):
        credentials = get_credentials()
        authorized_http = credentials.authorize(httplib2.Http())
        self.service = discovery.build('drive', 'v3', http=authorized_http)

    def create_folder(self, folder, parent):
        """Create a folder."""
        metadata = {
            'name': folder,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent],
        }
        resp = self.service.files().create(body=metadata, fields='id').execute()
        return resp['id']

    def upload(self, filepath, folder):
        """Upload a file to a specific folder."""
        filename = os.path.basename(filepath)

        mime_type = 'application/pdf'
        media = http.MediaFileUpload(filepath, mimetype=mime_type, resumable=True)
        metadata = {
            'name': filename,
            'parents': [folder],
        }

        self.service.files().create(body=metadata, media_body=media).execute()

    def list_folder(self, folder_id):
        """Get the active items in a folder."""
        files = self.service.files()
        request = files.list(
            pageSize=50, q="trashed = false and '{}' in parents".format(folder_id),
            fields="nextPageToken, files(id, name, mimeType, size)")

        all_items = []
        while request is not None:
            results = request.execute()
            all_items.extend(results['files'])
            request = files.list_next(request, results)

        return all_items


def upload_invoice(filepath, invoice_date):
    """Upload an invoice to the the month folder in Google Drive."""
    explorer = Explorer()

    month_folder = invoice_date.strftime('%Y%m')

    # get the id of the month folder (or create it)
    base_folder = settings.INVOICES_GDRIVE['folder_id']
    for folder in explorer.list_folder(base_folder):
        if month_folder == folder['name']:
            folder_id = folder['id']
            break
    else:
        folder_id = explorer.create_folder(month_folder, base_folder)

    # upload!
    explorer.upload(filepath, folder_id)
