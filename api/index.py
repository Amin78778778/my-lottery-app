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

def save_user_tickets(user_id, ticket_list):
    """İstifadəçinin aldığı biletləri onun ID-si altında bazaya yazır."""
    try:
        ref = db.reference(f'user_tickets/{user_id}')
        existing_tickets = ref.get() or []
        # Köhnə biletlərin üzərinə yenilərini əlavə edirik
        updated_tickets = existing_tickets + ticket_list
        ref.set(updated_tickets)
    except Exception as e:
        print(f"Bilet saxlama xətası: {e}")

def get_user_tickets(user_id):
    """İstifadəçinin bütün biletlərini bazadan çəkir."""
    try:
        ref = db.reference(f'user_tickets/{user_id}')
        tickets = ref.get()
        return tickets if tickets else []
    except:
        return []

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update:
        return "OK", 200

    if "pre_checkout_query" in update:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                     data={"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})
        return "OK", 200

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]

        # --- 1. ÖDƏNİŞ UĞURLU OLANDA ---
        if "successful_payment" in msg:
            payload = msg["successful_payment"]["invoice_payload"]
            bought_count = int(payload.split('_')[1])
            
            left, last_no = get_db_values()
            start_no = last_no + 1
            end_no = last_no + bought_count
            new_nos = list(range(start_no, end_no + 1))
            
            # Bazanı yeniləyirik (Qalan say və Sonuncu nömrə)
            db.reference('/').update({
                'tickets_left': max(0, left - bought_count),
                'last_ticket_no': end_no
            })
            
            # İstifadəçinin şəxsi siyahısına biletləri əlavə edirik
            save_user_tickets(user_id, new_nos)
            
            nos_str = ", ".join([f"№{n}" for n in new_nos])
            success_msg = f"✅ **Ödəniş Təsdiqləndi!**\n\n🎫 Yeni biletləriniz: {nos_str}\n📉 Qalan ümumi bilet: {max(0, left - bought_count)} / 100"
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                         json={"chat_id": chat_id, "text": success_msg, "parse_mode": "Markdown"})
            return "OK", 200

        # --- 2. KOMANDALAR VƏ DÜYMƏLƏR ---
        if "text" in msg:
            text = msg["text"]
            
            if text == "/start":
                left, _ = get_db_values()
                welcome = f"🌟 **NFT Lottery Aze** 🌟\n\n🎟 Qalan bilet: **{left} / 100**\n💎 Qiymət: **5 Star**"
                markup = {
                    "keyboard": [
                        [{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}],
                        [{"text": "🎫 Biletlərim"}, {"text": "🔄 Yenilə"}]
                    ],
                    "resize_keyboard": True
                }
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": markup})

            elif text == "🎫 Biletlərim":
                user_tickets = get_user_tickets(user_id)
                if user_tickets:
                    tickets_str = ", ".join([f"№{n}" for n in user_tickets])
                    msg_text = f"👤 **Sizin Biletləriniz:**\n\n{tickets_str}\n\n🎟 Ümumi say: {len(user_tickets)} ədəd"
                else:
                    msg_text = "🤷‍♂️ Sizin hələ ki, biletiniz yoxdur."
                
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": msg_text, "parse_mode": "Markdown"})

            elif "Bilet (" in text:
                count = 5 if "5" in text else 1
                left, _ = get_db_values()
                if left < count:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "❌ Bilet bitib."})
                else:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendInvoice", data={
                        "chat_id": chat_id, "title": f"Lotereya Bileti ({count} ədəd)",
                        "description": "Ödənişdən sonra biletləriniz 'Biletlərim' bölməsinə əlavə olunacaq.",
                        "payload": f"lottery_{count}", "provider_token": "", "currency": "XTR",
                        "prices": json.dumps([{"label": "Bilet", "amount": count * 5}])
                    })

            elif text == "🔄 Yenilə":
                left, _ = get_db_values()
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": f"🎟 Qalan bilet: **{left} / 100**", "parse_mode": "Markdown"})

    return "OK", 200
