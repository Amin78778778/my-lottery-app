import json
import requests
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- FİREBASE STABİL BAĞLANTI ---
if not firebase_admin._apps:
    try:
        # Vercel-də credentials.Certificate(None) bəzən problem yarada bilər, 
        # ona görə ən sadə üsulla (App Default və ya URL) başladırıq.
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://my-lottery-db-default-rtdb.firebaseio.com'
    })
    except Exception as e:
        print(f"Firebase Init Error: {e}")

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

def get_tickets_count():
    """Bazada qalan bilet sayını oxuyur."""
    try:
        ref = db.reference('tickets_left')
        count = ref.get()
        return count if count is not None else 15
    except:
        return 15 # Xəta olsa standart 15 göstər

def update_tickets_count(bought_count):
    """Bilet sayını azaldır."""
    try:
        ref = db.reference('tickets_left')
        current = get_tickets_count()
        new_count = max(0, current - bought_count)
        ref.set(new_count)
        return new_count
    except:
        return 0

def send_invoice(chat_id, count):
    """İstifadəçiyə Telegram Stars fakturası göndərir."""
    current_tickets = get_tickets_count()
    
    if current_tickets < count:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      json={"chat_id": chat_id, "text": f"❌ Təəssüf ki, cəmi {current_tickets} bilet qalıb."})
        return

    price_amount = count * 5
    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
    
    payload = {
        "chat_id": chat_id,
        "title": f"Lotereya Bileti ({count} ədəd)",
        "description": f"Lotereyada iştirak üçün ödəniş edin. Qalan bilet: {current_tickets}",
        "payload": f"lottery_{count}",
        "provider_token": "", 
        "currency": "XTR",
        "prices": json.dumps([{"label": "Bilet", "amount": price_amount}])
    }
    r = requests.post(url, data=payload)
    print(f"Invoice Response: {r.text}")

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        
        # 1. Start Komandası
        if "text" in update["message"]:
            text = update["message"]["text"]
            
            if text == "/start":
                qalan = get_tickets_count()
                welcome_text = (
                    f"🌟 **NFT Lottery Aze** 🌟\n\n"
                    f"Lotereyada iştirak etmək üçün bilet sayını seçin. "
                    f"Hər ödənişdən sonra iştirakınız sistemdə qeydə alınır.\n\n"
                    f"📊 **Statistika:**\n"
                    f"🎟 Qalan bilet: **{qalan} / 15**\n"
                    f"💎 Qiymət: **5 Star**\n\n"
                    f"Seçim edin:"
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
                qalan = get_tickets_count()
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                              json={"chat_id": chat_id, "text": f"🎟 Hazırda qalan bilet: **{qalan}**", "parse_mode": "Markdown"})

        # 2. Ödəniş Uğurlu Olanda
        if "successful_payment" in update["message"]:
            payload = update["message"]["successful_payment"]["invoice_payload"]
            bought_count = int(payload.split('_')[1])
            yeni_say = update_tickets_count(bought_count)
            
            success_msg = (
                "🎊 **Ödəniş uğurlu!** 🎊\n\n"
                f"Sizin {bought_count} ədəd biletiniz qeydə alındı.\n"
                f"📉 Ümumi qalan bilet: {yeni_say}\n\n"
                "Uğurlar! 🚀"
            )
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": success_msg, "parse_mode": "Markdown"})

    # 3. Ödəniş Təsdiqi (Pre-checkout)
    if "pre_checkout_query" in update:
        query_id = update["pre_checkout_query"]["id"]
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                      data={"pre_checkout_query_id": query_id, "ok": True})

    return "OK", 200
