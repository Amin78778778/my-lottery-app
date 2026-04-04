import json
import requests
from flask import Flask, request
import firebase_admin
from firebase_admin import db

app = Flask(__name__)
session = requests.Session() # Bağlantını açıq saxlayır (Sürət üçün)

FB_URL = 'https://my-lottery-db-default-rtdb.firebaseio.com'
TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={'databaseURL': FB_URL})

def tg_post(method, data):
    """Telegram-a sürətli mesaj göndərmə."""
    try:
        session.post(f"{BASE_URL}/{method}", json=data, timeout=5)
    except:
        pass

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "OK", 200

    # 1. Ödəniş sorğusuna dərhal (0.1 saniyədə) cavab ver
    if "pre_checkout_query" in update:
        tg_post("answerPreCheckoutQuery", {"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})
        return "OK", 200

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(msg["from"]["id"])

        # 2. ÖDƏNİŞ PROSESİ (Ən sürətli emal)
        if "successful_payment" in msg:
            payload = msg["successful_payment"]["invoice_payload"]
            count = int(payload.split('_')[1])
            
            # Baza əməliyyatlarını qruplaşdırırıq
            root = db.reference('/')
            data = root.get() or {}
            left = int(data.get('tickets_left', 100))
            last_no = int(data.get('last_ticket_no', 0))
            
            new_nos = list(range(last_no + 1, last_no + count + 1))
            user_ref = db.reference(f'user_tickets/{user_id}')
            
            # Update-ləri bir dəfəyə göndəririk
            root.update({'tickets_left': max(0, left - count), 'last_ticket_no': last_no + count})
            user_ref.set((user_ref.get() or []) + new_nos)
            
            tg_post("sendMessage", {"chat_id": chat_id, "text": f"✅ **Uğurlu!**\nBiletləriniz: {new_nos}", "parse_mode": "Markdown"})
            return "OK", 200

        # 3. MENYU VƏ KOMANDALAR
        if "text" in msg:
            text = msg["text"]
            if text in ["/start", "🔄 Yenilə"]:
                left = db.reference('tickets_left').get() or 100
                markup = {"keyboard": [[{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}], [{"text": "🎫 Biletlərim"}, {"text": "🔄 Yenilə"}]], "resize_keyboard": True}
                tg_post("sendMessage", {"chat_id": chat_id, "text": f"🌟 **Qalan bilet:** {left} / 100", "reply_markup": markup})
            
            elif text == "🎫 Biletlərim":
                tickets = db.reference(f'user_tickets/{user_id}').get() or []
                res = ", ".join([f"№{n}" for n in tickets]) if tickets else f"Bilet yoxdur. (ID: {user_id})"
                tg_post("sendMessage", {"chat_id": chat_id, "text": f"🎫 **Biletləriniz:**\n{res}"})

            elif "Bilet" in text:
                count = 5 if "5" in text else 1
                invoice = {
                    "chat_id": chat_id, "title": "Bilet", "description": f"{count} ədəd",
                    "payload": f"lottery_{count}", "provider_token": "", "currency": "XTR",
                    "prices": [{"label": "Bilet", "amount": count * 5}]
                }
                tg_post("sendInvoice", invoice)

    return "OK", 200
