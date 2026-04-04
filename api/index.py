import json
import requests
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- FİREBASE BAĞLANTISI (Şəkildəki real linkin) ---
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

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update:
        return "OK", 200

    # 1. Ödəniş öncəsi təsdiq (Vacib!)
    if "pre_checkout_query" in update:
        query_id = update["pre_checkout_query"]["id"]
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                     data={"pre_checkout_query_id": query_id, "ok": True})
        return "OK", 200

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        # 2. ÖDƏNİŞ UĞURLU OLANDA - BAZANI YENİLƏ
        if "successful_payment" in msg:
            try:
                payload = msg["successful_payment"]["invoice_payload"]
                bought_count = int(payload.split('_')[1])
                
                # Mövcud dəyərləri alaq
                left, last_no = get_db_values()
                
                # Yeni nömrələri hesablayaq
                start_no = last_no + 1
                end_no = last_no + bought_count
                nos_str = ", ".join([f"№{n}" for n in range(start_no, end_no + 1)])
                new_left = max(0, left - bought_count)
                
                # BAZAYA MƏCBURİ YAZIRIQ
                db.reference('/').update({
                    'tickets_left': new_left,
                    'last_ticket_no': end_no
                })
                
                success_msg = f"✅ **Ödəniş Təsdiqləndi!**\n\n🎫 Biletləriniz: {nos_str}\n📉 Qalan bilet: {new_left} / 100"
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": success_msg, "parse_mode": "Markdown"})
            except Exception as e:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": f"Xəta: {str(e)}"})
            return "OK", 200

        # 3. MƏTN KOMANDALARI
        if "text" in msg:
            text = msg["text"]
            
            if text == "/start":
                left, _ = get_db_values()
                welcome = f"🌟 **NFT Lottery Aze** 🌟\n\n🎟 Qalan bilet: **{left} / 100**\n💎 Qiymət: **5 Star**"
                markup = {
                    "keyboard": [[{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}], [{"text": "🔄 Yenilə"}]],
                    "resize_keyboard": True
                }
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": markup})

            elif "Bilet" in text:
                count = 5 if "5" in text else 1
                left, _ = get_db_values()
                if left < count:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "❌ Bilet bitib."})
                else:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendInvoice", data={
                        "chat_id": chat_id, "title": f"Lotereya Bileti ({count} ədəd)",
                        "description": "Bilet nömrələri ödənişdən sonra təqdim olunur.",
                        "payload": f"lottery_{count}", "provider_token": "", "currency": "XTR",
                        "prices": json.dumps([{"label": "Bilet", "amount": count * 5}])
                    })

            elif "Yenilə" in text:
                left, _ = get_db_values()
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": f"🎟 Qalan bilet: **{left} / 100**", "parse_mode": "Markdown"})

    return "OK", 200
