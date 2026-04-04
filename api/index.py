import json
import requests
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- FİREBASE BAĞLANTISI (Sığortalı) ---
FB_URL = 'https://my-lottery-db-default-rtdb.firebaseio.com'

if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app(options={'databaseURL': FB_URL})
    except Exception as e:
        print(f"Firebase Init Error: {e}")

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

def get_db_values():
    """Bazada bilet sayını yoxlayır, xəta olsa 100 qaytarır ki bot donmasın."""
    try:
        ref = db.reference('/')
        data = ref.get()
        if data:
            left = data.get('tickets_left', 100)
            last_no = data.get('last_ticket_no', 0)
            return int(left), int(last_no)
    except Exception as e:
        print(f"DB Read Error: {e}")
    return 100, 0

def process_purchase(bought_count):
    """Biletləri azaldır və ardıcıl nömrələri təyin edir."""
    try:
        left, last_no = get_db_values()
        start_no = last_no + 1
        end_no = last_no + bought_count
        ticket_numbers = list(range(start_no, end_no + 1))
        
        new_left = max(0, left - bought_count)
        ref = db.reference('/')
        ref.update({
            'tickets_left': new_left,
            'last_ticket_no': end_no
        })
        return ticket_numbers, new_left
    except Exception as e:
        print(f"DB Update Error: {e}")
        return [], 0

@app.route('/api', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if not update:
            return "OK", 200

        # --- 1. ÖDƏNİŞ ÖNCƏSİ TƏSDİQ (Donmaması üçün ən vacib hissə) ---
        if "pre_checkout_query" in update:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                         data={"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})
            return "OK", 200

        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            
            # --- 2. ÖDƏNİŞ UĞURLU OLANDA ---
            if "successful_payment" in msg:
                payload = msg["successful_payment"]["invoice_payload"]
                count = int(payload.split('_')[1])
                nos, left = process_purchase(count)
                nos_str = ", ".join([f"№{n}" for n in nos])
                
                res_msg = f"✅ **Ödəniş Uğurlu!**\n\n🎫 Biletləriniz: {nos_str}\n📉 Qalan: {left} / 100"
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": res_msg, "parse_mode": "Markdown"})
                return "OK", 200

            # --- 3. MƏTN KOMANDALARI ---
            if "text" in msg:
                text = msg["text"]
                
                if text == "/start":
                    left, _ = get_db_values()
                    welcome = (f"🌟 **NFT Lottery Aze** 🌟\n\n🎟 Qalan bilet: **{left} / 100**\n"
                               f"💎 Qiymət: **5 Star**\n\nBilet sayını seçin:")
                    markup = {
                        "keyboard": [[{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}], 
                                     [{"text": "🎟 10 Bilet (50 ⭐)"}], [{"text": "🔄 Yenilə"}]],
                        "resize_keyboard": True
                    }
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                 json={"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown", "reply_markup": markup})

                elif "Bilet" in text:
                    count = 10 if "10" in text else (5 if "5" in text else 1)
                    left, _ = get_db_values()
                    if left < count:
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                     json={"chat_id": chat_id, "text": f"❌ Cəmi {left} bilet qalıb."})
                    else:
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendInvoice", data={
                            "chat_id": chat_id, "title": f"Lotereya Bileti ({count} ədəd)",
                            "description": "Bilet nömrələri ödənişdən sonra veriləcək.",
                            "payload": f"lottery_{count}", "provider_token": "", "currency": "XTR",
                            "prices": json.dumps([{"label": "Bilet", "amount": count * 5}])
                        })

                elif "Yenilə" in text:
                    left, _ = get_db_values()
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                 json={"chat_id": chat_id, "text": f"🎟 Qalan bilet: **{left} / 100**", "parse_mode": "Markdown"})

    except Exception as global_e:
        print(f"Global Error: {global_e}")

    return "OK", 200
