import json
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    
    # 1. WebApp-dan gələn məlumatı tutmaq
    if "message" in update and "web_app_data" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        raw_data = update["message"]["web_app_data"]["data"]
        
        try:
            data = json.loads(raw_data)
            if data.get("action") == "buy_stars":
                # Telegram-a Ödəmə Fakturası göndəririk
                url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
                payload = {
                    "chat_id": chat_id,
                    "title": "Lotereya Bileti",
                    "description": f"{data['count']} ədəd bilet alışı",
                    "payload": "lottery_ticket_payment",
                    "provider_token": "", # Stars üçün boş qalmalıdır
                    "currency": "XTR",    # Telegram Stars kodu
                    "prices": json.dumps([{"label": "Bilet", "amount": int(data['total_price'])}])
                }
                requests.post(url, data=payload)
        except Exception:
            pass

    # 2. Ödəniş öncəsi təsdiq (Pre-checkout) - BU HİSSƏ MÜTLƏQDİR
    if "pre_checkout_query" in update:
        query_id = update["pre_checkout_query"]["id"]
        url = f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery"
        requests.post(url, data={"pre_checkout_query_id": query_id, "ok": True})

    return "OK", 200
