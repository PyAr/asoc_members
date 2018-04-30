import csv

from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

# Please, adjust this values:
SPREADSHEET_ID = '1eewdZtKJY3cDOiRaB6sAYo2lQ7jTEeZoV4f-U1dzRIY'
RANGE_NAME = 'Humanos!A2:T'

# Setup the Sheets API
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
store = file.Storage('credentials.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
    creds = tools.run_flow(flow, store)
service = build('sheets', 'v4', http=creds.authorize(Http()))

# Call the Sheets API
result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,
                                             range=RANGE_NAME).execute()
values = result.get('values', [])
if not values:
    print('No data found.')
else:
    with open('ac_members.csv', 'w') as f:
        writer = csv.writer(f)
        for row in values:
            writer.writerow(row)
