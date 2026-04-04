import json
import requests
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- FİREBASE KONFİQURASİYASI ---
if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app(options={
            'databaseURL': 'https://my-lottery-db-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        print(f"Firebase Init Error: {e}")

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

def get_db_values():
    """Bazada bilet sayını və sonuncu nömrəni yoxlayır."""
    try:
        ref = db.reference('/')
        data = ref.get()
        if not data:
            return 100, 0
        left = data.get('tickets_left', 100)
        last_no = data.get('last_ticket_no', 0)
        return int(left), int(last_no)
    except:
        return 100, 0

def process_purchase(bought_count):
    """Biletləri azaldır və ardıcıl nömrələri təyin edir."""
    left, last_no = get_db_values()
    start_no = last_no + 1
    end_no = last_no + bought_count
    ticket_numbers = list(range(start_no, end_no + 1))
    
    ref = db.reference('/')
    new_left = max(0, left - bought_count)
    ref.update({
        'tickets_left': new_left,
        'last_ticket_no': end_no
    })
    return ticket_numbers, new_left

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update:
        return "OK", 200

    if "message" in update:
        msg_data = update["message"]
        chat_id = msg_data["chat"]["id"]
        
        # 1. Mətn Mesajları (Menyu)
        if "text" in msg_data:
            text = msg_data["text"]
            
            if text == "/start":
                left, _ = get_db_values()
                welcome_text = (
                    f"🌟 **NFT Lottery Aze** 🌟\n\n"
                    f"Lotereyamızda iştirak üçün bilet əldə edə bilərsiniz.\n\n"
                    f"📊 **Statistika:**\n"
                    f"🎟 Ümumi bilet: **100**\n"
                    f"🎟 Qalan bilet: **{left} / 100**\n"
                    f"💎 Bilet qiyməti: **5 Star**\n\n"
                    "Bilet sayını seçin:"
                )
                reply_markup = {
                    "keyboard": [
                        [{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}],
                        [{"text": "🎟 10 Bilet (50 ⭐)"}],
                        [{"text": "🔄 Yenilə / Sayı Yoxla"}]
                    ],
                    "resize_keyboard": True
                }
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": welcome_text, "parse_mode": "Markdown", "reply_markup": reply_markup})

            elif "Bilet" in text:
                # Seçilən bilet sayını tapırıq
                count = 1
                if "5 Bilet" in text: count = 5
                elif "10 Bilet" in text: count = 10
                
                left, _ = get_db_values()
                if left < count:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                 json={"chat_id": chat_id, "text": f"❌ Təəssüf ki, cəmi {left} bilet qalıb."})
                else:
                    # Stars Fakturası göndərilir
                    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
                    payload = {
                        "chat_id": chat_id,
                        "title": f"Lotereya Bileti ({count} ədəd)",
                        "description": f"Cəmi {count * 5} Star. Ödənişdən sonra ardıcıl nömrələriniz veriləcək.",
                        "payload": f"lottery_{count}",
                        "provider_token": "", 
                        "currency": "XTR",
                        "prices": json.dumps([{"label": "Bilet", "amount": count * 5}])
                    }
                    requests.post(url, data=payload)

            elif "Yenilə" in text:
                left, _ = get_db_values()
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             json={"chat_id": chat_id, "text": f"🎟 Hazırda qalan bilet: **{left} / 100**", "parse_mode": "Markdown"})

        # 2. Ödəniş Uğurlu Olanda
        if "successful_payment" in msg_data:
            inv_payload = msg_data["successful_payment"]["invoice_payload"]
            bought_count = int(inv_payload.split('_')[1])
            
            # Nömrələri generasiya edirik və bazanı yeniləyirik
            nos, new_left = process_purchase(bought_count)
            nos_str = ", ".join([f"№{n}" for n in nos])
            
            success_msg = (
                "🎊 **Ödəniş Uğurlu!** 🎊\n\n"
                f"🎫 **Sizin Bilet Nömrələriniz:** {nos_str}\n"
                f"📉 **Qalan ümumi bilet:** {new_left} / 100\n\n"
                "Uğurlar arzulayırıq! 🚀"
            )
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                         json={"chat_id": chat_id, "text": success_msg, "parse_mode": "Markdown"})

    # 3. Pre-checkout (Telegram-ın ödəniş təsdiqi)
    if "pre_checkout_query" in update:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                     data={"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})

    return "OK", 200
