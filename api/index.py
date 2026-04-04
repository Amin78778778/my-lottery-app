import json
import requests
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- FİREBASE SAZLAMALARI ---
if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app(options={
            'databaseURL': 'https://my-lottery-db-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        print(f"Firebase xətası: {e}")

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

def get_db_values():
    try:
        ref = db.reference('/')
        data = ref.get()
        if not data:
            return 15, 0
        left = data.get('tickets_left', 15)
        last_no = data.get('last_ticket_no', 0)
        return int(left), int(last_no)
    except:
        return 15, 0

def process_purchase(bought_count):
    left, last_no = get_db_values()
    start_no = last_no + 1
    end_no = last_no + bought_count
    ticket_numbers = list(range(start_no, end_no + 1))
    
    ref = db.reference('/')
    ref.update({
        'tickets_left': max(0, left - bought_count),
        'last_ticket_no': end_no
    })
    return ticket_numbers, max(0, left - bought_count)

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update:
        return "OK", 200

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        
        if "text" in update["message"]:
            text = update["message"]["text"]
            
            if text == "/start":
                left, _ = get_db_values()
                welcome_text = (
                    f"🌟 **NFT Lottery Aze** 🌟\n\n"
                    f"🎟 Qalan bilet: **{left} / 15**\n"
                    f"💎 Qiymət: **5 Star**\n\n"
                    "Bilet almaq üçün aşağıdan seçim edin:"
                )
                reply_markup = {
                    "keyboard": [[{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}], [{"text": "🔄 Yenilə"}]],
                    "resize_keyboard": True
                }
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": welcome_text, "parse_mode": "Markdown", "reply_markup": reply_markup})

            elif "Bilet" in text:
                count = 1 if "1 Bilet" in text else 5
                left, _ = get_db_values()
                if left < count:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "❌ Kifayət qədər bilet qalmayıb."})
                else:
                    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
                    payload = {
                        "chat_id": chat_id, "title": f"Lotereya Bileti ({count} ədəd)",
                        "description": "Ödənişdən sonra bilet nömrələriniz veriləcək.",
                        "payload": f"lottery_{count}", "provider_token": "", "currency": "XTR",
                        "prices": json.dumps([{"label": "Bilet", "amount": count * 5}])
                    }
                    requests.post(url, data=payload)

            elif "Yenilə" in text:
                left, _ = get_db_values()
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"🎟 Qalan bilet: {left}"})

        if "successful_payment" in update["message"]:
            inv_payload = update["message"]["successful_payment"]["invoice_payload"]
            bought_count = int(inv_payload.split('_')[1])
            nos, new_left = process_purchase(bought_count)
            nos_str = ", ".join([f"№{n}" for n in nos])
            msg = f"✅ **Ödəniş Uğurlu!**\n\n🎫 Biletləriniz: {nos_str}\n📉 Qalan: {new_left}"
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

    if "pre_checkout_query" in update:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                     data={"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})

    return "OK", 200
