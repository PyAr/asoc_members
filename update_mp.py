import os
from dotenv import load_dotenv
from mercadopago import MP
load_dotenv()

MERCADOPAGO_CLIENT_ID = os.getenv('MERCADOPAGO_CLIENT_ID')
MERCADOPAGO_CLIENT_SECRET = os.getenv('MERCADOPAGO_CLIENT_SECRET')

mp = MP(MERCADOPAGO_CLIENT_ID, MERCADOPAGO_CLIENT_SECRET)
mp_access_token = mp.get_access_token()
response = mp.get('/v1/payments/search')
print(response)
