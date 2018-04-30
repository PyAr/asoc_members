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
        "limit": 1
    }

response = mp.search_payment(filters, 
                             limit=filters["limit"],
                             offset=filters["offset"])
#response = mp.search_payment(filters)
#json_response = json.dumps(response, indent=4)
payment = {
        "timestamp": response["response"]["results"][0]["collection"]["date_approved"],
        "amount": response["response"]["results"][0]["collection"]["total_paid_amount"],
        "strategy": {
            "id": response["response"]["results"][0]["collection"]["payer"]["id"],
            "comment": response["response"]["results"][0]["collection"]["operation_type"],
            "patron": {
                "name": response["response"]["results"][0]["collection"]["cardholder"]["name"],
                "email": response["response"]["results"][0]["collection"]["payer"]["email"],
                "comment": response["response"]["results"][0]["collection"]["cardholder"]["identification"]["type"] + response["response"]["results"][0]["collection"]["cardholder"]["identification"]["number"],
            },
        },
        "comment": response["response"]["results"][0]["collection"]["reason"],
    }

print(json.dumps(payment, indent=2))
