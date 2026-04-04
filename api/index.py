import json
import requests
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# --- FİREBASE AYARLARI ---
if not firebase_admin._apps:
    # databaseURL hissəsinə öz Firebase linkinizi qeyd edin
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://lottery-aze-default-rtdb.firebaseio.com'
    })

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

def get_tickets_count():
    """Bazada qalan bilet sayını oxuyur."""
    ref = db.reference('tickets_left')
    count = ref.get()
    return count if count is not None else 15

def update_tickets_count(bought_count):
    """Bilet sayını azaldır."""
    ref = db.reference('tickets_left')
    current = get_tickets_count()
    new_count = max(0, current - bought_count)
    ref.set(new_count)
    return new_count

def send_invoice(chat_id, count):
    """İstifadəçiyə ödəniş fakturası göndərir."""
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
        "description": f"Qalan bilet: {current_tickets}. Ödənişdən sonra iştirakınız təsdiqlənir.",
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

        # 1. Start və Məlumat Mesajı
        if text == "/start":
            qalan = get_tickets_count()
            welcome_text = (
                f"🌟 **NFT Lottery Aze-yə Xoş Gəldiniz!** 🌟\n\n"
                f"Siz Telegram Stars vasitəsilə lotereyada iştirak edə bilərsiniz. 🚀\n\n"
                f"📊 **Statistika:**\n"
                f"🎟 Qalan bilet: **{qalan} / 15**\n"
                f"💎 Bilet qiyməti: **5 Star**\n\n"
                f"Bilet almaq üçün aşağıdakı menyudan seçim edin:"
            )
            reply_markup = {
                "keyboard": [
                    [{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}],
                    [{"text": "🔄 Yenilə / Qalan Bilet"}]
                ],
                "resize_keyboard": True
            }
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": welcome_text, "parse_mode": "Markdown", "reply_markup": reply_markup})

        # 2. Seçimlərə Reaksiya
        elif "1 Bilet" in text:
            send_invoice(chat_id, 1)
        elif "5 Bilet" in text:
            send_invoice(chat_id, 5)
        elif "Yenilə" in text:
            qalan = get_tickets_count()
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": f"🎟 Hazırda qalan bilet sayı: **{qalan}**", "parse_mode": "Markdown"})

        # 3. Ödəniş Uğurlu Olanda Göndərilən Təsdiq
        if "successful_payment" in update["message"]:
            payload = update["message"]["successful_payment"]["invoice_payload"]
            bought_count = int(payload.split('_')[1])
            yeni_say = update_tickets_count(bought_count)
            
            success_msg = (
                "🎊 **Təbriklər!** 🎊\n\n"
                "Ödənişiniz uğurla tamamlandı. Artıq uduş fonduna daxil edildiniz.\n\n"
                f"🎫 **Bilet sayınız:** {bought_count}\n"
                f"📉 **Ümumi qalan bilet:** {yeni_say}\n\n"
                "Uğurlar arzulayırıq! 🚀"
            )
            
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": success_msg, "parse_mode": "Markdown"})

    # 4. Ödəniş Öncesi Təsdiq (Telegram tələbi)
    if "pre_checkout_query" in update:
        query_id = update["pre_checkout_query"]["id"]
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                      data={"pre_checkout_query_id": query_id, "ok": True})

    return "OK", 200
