import json
import requests
from flask import Flask, request
import firebase_admin
from firebase_admin import db

app = Flask(__name__)

FB_URL = 'https://my-lottery-db-default-rtdb.firebaseio.com'
TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app(options={'databaseURL': FB_URL})
    except:
        pass

def get_db_values():
    try:
        data = db.reference('/').get()
        if data:
            return int(data.get('tickets_left', 100)), int(data.get('last_ticket_no', 0))
    except:
        pass
    return 100, 0

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "OK", 200

    if "pre_checkout_query" in update:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                     data={"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})
        return "OK", 200

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(msg["from"]["id"])

        if "successful_payment" in msg:
            try:
                count = int(msg["successful_payment"]["invoice_payload"].split('_')[1])
                left, last_no = get_db_values()
                new_nos = list(range(last_no + 1, last_no + count + 1))
                db.reference('/').update({'tickets_left': max(0, left - count), 'last_ticket_no': last_no + count})
                
                ref = db.reference(f'user_tickets/{user_id}')
                current = ref.get() or []
                ref.set(current + new_nos)
                
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": f"✅ Uğurlu! Biletləriniz: {new_nos}"})
            except:
                pass
            return "OK", 200

        if "text" in msg:
            text = msg["text"]
            if text == "/start" or text == "🔄 Yenilə":
                left, _ = get_db_values()
                markup = {"keyboard": [[{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}], [{"text": "🎫 Biletlərim"}, {"text": "🔄 Yenilə"}]], "resize_keyboard": True}
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": f"🌟 Qalan bilet: {left}", "reply_markup": markup})
            
            elif text == "🎫 Biletlərim":
                tickets = db.reference(f'user_tickets/{user_id}').get() or []
                res = ", ".join([f"№{n}" for n in tickets]) if tickets else f"Bilet yoxdur. (ID: {user_id})"
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"🎫 Biletləriniz: {res}"})

            elif "Bilet" in text:
                count = 5 if "5" in text else 1
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendInvoice", data={
                    "chat_id": chat_id, "title": "Bilet", "description": f"{count} ədəd",
                    "payload": f"lottery_{count}", "provider_token": "", "currency": "XTR",
                    "prices": json.dumps([{"label": "Bilet", "amount": count * 5}])
                })

    return "OK", 200
