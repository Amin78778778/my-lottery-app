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
    print(f"TELEGRAM_RESPONSE: {r.text}")

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    print(f"NEW_LOG: {json.dumps(update)}")
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        
        # ƏSAS HİSSƏ: WebApp-dan gələn məlumatı yoxlayırıq
        if "web_app_data" in update["message"]:
            data_str = update["message"]["web_app_data"]["data"]
            print(f"DATA_FOUND: {data_str}")
            try:
                data = json.loads(data_str)
                send_invoice(chat_id, data.get("count"), data.get("total_price"))
            except Exception as e:
                print(f"ERROR: {e}")
        
        # Sadə mesajlar üçün (Test)
        elif "text" in update["message"] and update["message"]["text"] == "/start":
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          data={"chat_id": chat_id, "text": "Bot hazır! İndi bilet alaraq yoxlayın."})

    if "pre_checkout_query" in update:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                      data={"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})

    return "OK", 200
