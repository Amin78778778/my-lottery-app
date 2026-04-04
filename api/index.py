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
    """Bazada qalan bilet sayını və sonuncu bilet nömrəsini alır."""
    ref = db.reference('/')
    data = ref.get()
    if not data:
        return 15, 0 # Standart: 15 bilet qalıb, sonuncu nömrə 0
    
    left = data.get('tickets_left', 15)
    last_no = data.get('last_ticket_no', 0)
    return left, last_no

def process_purchase(bought_count):
    """Bilet sayını azaldır və yeni bilet nömrələrini generasiya edir."""
    left, last_no = get_db_values()
    
    # Yeni bilet nömrələri ardıcıllığı
    start_no = last_no + 1
    end_no = last_no + bought_count
    ticket_numbers = list(range(start_no, end_no + 1))
    
    # Bazanı yeniləyirik
    ref = db.reference('/')
    ref.update({
        'tickets_left': max(0, left - bought_count),
        'last_ticket_no': end_no
    })
    
    return ticket_numbers, max(0, left - bought_count)

def send_invoice(chat_id, count):
    left, _ = get_db_values()
    
    if left < count:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      json={"chat_id": chat_id, "text": f"❌ Təəssüf ki, cəmi {left} bilet qalıb."})
        return

    price_amount = count * 5
    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
    payload = {
        "chat_id": chat_id,
        "title": f"Lotereya Bileti ({count} ədəd)",
        "description": f"Seçilən bilet sayı: {count}. Ödənişdən sonra nömrələriniz təqdim olunacaq.",
        "payload": f"lottery_{count}",
        "provider_token": "", 
        "currency": "XTR",
        "prices": json.dumps([{"label": "Bilet", "amount": price_amount}])
    }
    requests.post(url, data=payload)

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if text == "/start":
            left, _ = get_db_values()
            welcome_text = (
                f"🌟 **NFT Lottery Aze** 🌟\n\n"
                f"📊 **Statistika:**\n"
                f"🎟 Qalan bilet: **{left} / 15**\n"
                f"💎 Qiymət: **5 Star**\n\n"
                f"Bilet almaq üçün aşağıdan seçim edin:"
            )
            reply_markup = {
                "keyboard": [
                    [{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}],
                    [{"text": "🔄 Yenilə / Sayı Yoxla"}]
                ],
                "resize_keyboard": True
            }
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": welcome_text, "parse_mode": "Markdown", "reply_markup": reply_markup})

        elif "1 Bilet" in text:
            send_invoice(chat_id, 1)
        elif "5 Bilet" in text:
            send_invoice(chat_id, 5)
        elif "Yenilə" in text:
            left, _ = get_db_values()
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": f"🎟 Hazırda qalan bilet: **{left}**", "parse_mode": "Markdown"})

        # --- ÖDƏNİŞ UĞURLU OLANDA ---
        if "successful_payment" in update["message"]:
            payload = update["message"]["successful_payment"]["invoice_payload"]
            bought_count = int(payload.split('_')[1])
            
            # Bilet nömrələrini və yeni sayını alırıq
            nos, new_left = process_purchase(bought_count)
            nos_str = ", ".join([f"№{n}" for n in nos])
            
            success_msg = (
                "🎊 **Ödəniş Uğurlu Oldu!** 🎊\n\n"
                f"🎫 **Sizin Bilet Nömrələriniz:** {nos_str}\n"
                f"📉 **Qalan ümumi bilet:** {new_left}\n\n"
                "Uğurlar arzulayırıq! 🚀"
            )
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": success_msg, "parse_mode": "Markdown"})

    if "pre_checkout_query" in update:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                      data={"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})

    return "OK", 200
