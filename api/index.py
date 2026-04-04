import json
import requests
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- FİREBASE KONFİQURASİYASI ---
FB_URL = 'https://my-lottery-db-default-rtdb.firebaseio.com'

if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app(options={'databaseURL': FB_URL})
    except Exception as e:
        print(f"Firebase Init Error: {e}")

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

def get_db_values():
    try:
        ref = db.reference('/')
        data = ref.get()
        if data:
            left = data.get('tickets_left', 100)
            last_no = data.get('last_ticket_no', 0)
            return int(left), int(last_no)
    except:
        pass
    return 100, 0

def get_user_tickets(user_id):
    try:
        ref = db.reference(f'user_tickets/{user_id}')
        tickets = ref.get()
        return tickets if isinstance(tickets, list) else []
    except:
        return []

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

        # --- ÖDƏNİŞİN QƏBULU ---
        if "successful_payment" in msg:
            payload = msg["successful_payment"]["invoice_payload"]
            count = int(payload.split('_')[1])
            left, last_no = get_db_values()
            new_nos = list(range(last_no + 1, last_no + count + 1))
            
            db.reference('/').update({
                'tickets_left': max(0, left - count),
                'last_ticket_no': last_no + count
            })
            
            # Biletləri istifadəçiyə bağla
            ref = db.reference(f'user_tickets/{user_id}')
            current = ref.get() or []
            ref.set(current + new_nos)
            
            nos_str = ", ".join([f"№{n}" for n in new_nos])
            res = f"✅ **Ödəniş Təsdiqləndi!**\n\n🎫 Biletləriniz: {nos_str}\n📉 Qalan: {max(0, left - count)} / 100"
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": res, "parse_mode": "Markdown"})
            return "OK", 200

        if "text" in msg:
            text = msg["text"]
            
            if text == "/start":
                left, _ = get_db_values()
                welcome = f"🌟 **NFT Lottery Aze** 🌟\n\n🎟 Qalan bilet: **{left} / 100**\n💎 1 Bilet: **5 Star**"
                markup = {"keyboard": [[{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}], [{"text": "🎫 Biletlərim"}, {"text": "🔄 Yenilə"}]], "resize_keyboard": True}
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": markup})

            elif text == "🎫 Biletlərim":
                tickets = get_user_tickets(user_id)
                if tickets:
                    msg_text = f"👤 **Sizin Biletləriniz:**\n\n" + ", ".join([f"№{n}" for n in tickets])
                else:
                    msg_text = f"🤷‍♂️ Biletiniz yoxdur.\n(Sizin ID: `{user_id}`)"
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": msg_text, "parse_mode": "Markdown"})

            elif "Bilet" in text:
                # Dəqiq say tapma
                count = 1
                if "5 Bilet" in text: count = 5
                
                left, _ = get_db_values()
                if left < count:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "❌ Kifayət qədər bilet yoxdur."})
                else:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendInvoice", data={
                        "chat_id": chat_id, 
                        "title": f"Bilet Alışı ({count} ədəd)",
                        "description": f"{count} ədəd lotereya bileti.",
                        "payload": f"lottery_{count}", 
                        "provider_token": "", 
                        "currency": "XTR",
                        "prices": json.dumps([{"label": "Bilet", "amount": count * 5}])
                    })

            elif text == "🔄 Yenilə":
                left, _ = get_db_values()
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"🎟 Qalan bilet: **{left} / 100**", "parse_mode": "Markdown"})

    return "OK", 200
