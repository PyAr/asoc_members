#!/usr/bin/env fades

"""Script de ayuda para la carga inicial de Miembros.

Al inicio de los tiempos existía una planilla en GDrive... y tuvimos que cargarla.
Después no usamos más esto...

fades:
    google-api-python-client
    oauth2client
"""
import csv
import sys

from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools


DEFAULT_SPREADSHEET = '16hC6CUFksOGctFbKZNuvWjfi6Yzdsfv4yYyYWVHKezM'


def download_spreadsheet(spreadsheet_id):
    # Please, adjust this values as needed:
    RANGE_NAME = 'Humanos!A1:T'

    # Setup the Sheets API
    SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('sheets', 'v4', http=creds.authorize(Http()))

    # Call the Sheets API
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=RANGE_NAME).execute()
    values = result.get('values', [])

    return values


if __name__ == "__main__":
    spreadsheet_id = DEFAULT_SPREADSHEET
    if len(sys.argv) > 1:
        spreadsheet_id = sys.argv[1]

    values = download_spreadsheet(spreadsheet_id)
    with open('ac_members.csv', 'w') as f:
        writer = csv.writer(f)
        for row in values:
            writer.writerow(row)
