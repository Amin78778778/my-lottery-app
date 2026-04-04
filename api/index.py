import json
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

def send_invoice(chat_id, count, total_price):
    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
    # Stars üçün qiymət mütləq integer olmalıdır
    try:
        price_amount = int(total_price)
    except:
        price_amount = 5
        
    payload = {
        "chat_id": chat_id,
        "title": "Lotereya Bileti",
        "description": f"{count} ədəd bilet alışı",
        "payload": "lottery_pay",
        "provider_token": "", 
        "currency": "XTR",
        "prices": json.dumps([{"label": "Bilet", "amount": price_amount}])
    }
    r = requests.post(url, data=payload)
    print(f"TELEGRAM_RESPONSE: {r.text}") # Əgər Telegram imtina etsə, səbəbi burada yazılacaq

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    print(f"FULL_UPDATE: {json.dumps(update)}") # Gələn bütün datanı logda görmək üçün
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        
        # WebApp-dan gələn datanı yoxlayırıq
        if "web_app_data" in update["message"]:
            raw_data = update["message"]["web_app_data"]["data"]
            print(f"WEBAPP_DATA_RECEIVED: {raw_data}")
            try:
                data = json.loads(raw_data)
                send_invoice(chat_id, data.get("count"), data.get("total_price"))
            except Exception as e:
                print(f"JSON_ERROR: {str(e)}")
        
        # Əgər sadə mesajdırsa (Test üçün)
        elif "text" in update["message"] and update["message"]["text"] == "/start":
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          data={"chat_id": chat_id, "text": "Xoş gəldiniz! Bilet almaq üçün düyməni sıxın."})

    if "pre_checkout_query" in update:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                      data={"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})

    return "OK", 200
