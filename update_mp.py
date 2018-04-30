#!/usr/bin/env python
import json
import os
from dotenv import load_dotenv
from mercadopago import MP
load_dotenv()

MERCADOPAGO_CLIENT_ID = os.getenv('MERCADOPAGO_CLIENT_ID')
MERCADOPAGO_CLIENT_SECRET = os.getenv('MERCADOPAGO_CLIENT_SECRET')

mp = MP(MERCADOPAGO_CLIENT_ID, MERCADOPAGO_CLIENT_SECRET)
#r = mp.get("/v1/payments/search")
#print(r)
filters = {
        "status": "approved",
        "offset": 0,
        "limit": 10
    }

response = mp.search_payment(filters, 
                             limit=filters["limit"],
                             offset=filters["offset"])
#response = mp.search_payment(filters)
json_response = json.dumps(response, indent=4)
print(json_response)
