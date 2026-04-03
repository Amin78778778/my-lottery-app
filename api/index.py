import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        
        # WebApp-dan gələn məlumatı tutmaq
        if "web_app_data" in update["message"]:
            raw_data = update["message"]["web_app_data"]["data"]
            data = json.loads(raw_data)
            
            if data.get("action") == "buy_stars":
                invoice_url = f"{TELEGRAM_API}/sendInvoice"
                payload = {
                    "chat_id": chat_id,
                    "title": "Lotereya Bileti",
                    "description": f"{data['count']} ədəd bilet alışı",
                    "payload": "lottery_ticket",
                    "currency": "XTR",
                    "prices": json.dumps([{"label": "Bilet", "amount": data['total_price']}]),
                    "provider_token": ""
                }
                requests.post(invoice_url, data=payload)

    # Ödəniş təsdiqi (Pre-checkout)
    if "pre_checkout_query" in update:
        query_id = update["pre_checkout_query"]["id"]
        confirm_url = f"{TELEGRAM_API}/answerPreCheckoutQuery"
        requests.post(confirm_url, data={"pre_checkout_query_id": query_id, "ok": True})

    return "OK", 200
