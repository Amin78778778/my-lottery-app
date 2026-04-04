import json
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

def send_invoice(chat_id, count, total_price):
    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
    payload = {
        "chat_id": chat_id,
        "title": "Lotereya Bileti",
        "description": f"{count} ədəd bilet alışı",
        "payload": "lottery_pay",
        "provider_token": "", 
        "currency": "XTR",
        "prices": json.dumps([{"label": "Bilet", "amount": int(total_price)}])
    }
    r = requests.post(url, data=payload)
    print(f"Invoice Response: {r.text}") # Bu Loglarda görünəcək

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    print(f"Update received: {json.dumps(update)}") # Gələn məlumatı görmək üçün
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        
        # WebApp-dan gələn məlumat
        if "web_app_data" in update["message"]:
            try:
                data = json.loads(update["message"]["web_app_data"]["data"])
                send_invoice(chat_id, data.get("count"), data.get("total_price"))
            except Exception as e:
                print(f"Error parsing data: {e}")
        
        # Sadə mesajlara cavab (Test üçün)
        else:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": chat_id, "text": "Bot işləyir! İndi WebApp-dan bilet alaraq yoxla."})

    if "pre_checkout_query" in update:
        url = f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery"
        requests.post(url, data={"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})

    return "OK", 200
