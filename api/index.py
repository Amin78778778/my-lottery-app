import json
import requests
from flask import Flask, request

app = Flask(__name__)

# Sizin Bot Tokeniniz
TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

def send_invoice(chat_id, count):
    # Hər bilet 5 ulduz (XTR)
    price_amount = count * 5
    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
    
    payload = {
        "chat_id": chat_id,
        "title": f"Lotereya Bileti ({count} ədəd)",
        "description": f"Uduşda iştirak etmək üçün {count} bilet alışı. Telegram Stars ilə ödəniş edin.",
        "payload": f"lottery_{count}",
        "provider_token": "", 
        "currency": "XTR",
        "prices": json.dumps([{"label": "Bilet", "amount": price_amount}])
    }
    r = requests.post(url, data=payload)
    print(f"Invoice Sent: {r.text}")

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        # 1. Start komandası və İnformasiya mətni
        if text == "/start":
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            
            welcome_text = (
                "🌟 **NFT Lottery Aze-yə Xoş Gəldiniz!** 🌟\n\n"
                "Bu bot vasitəsilə siz Telegram Stars (Ulduzlar) istifadə edərək "
                "eksklüziv NFT lotereyalarında iştirak edə bilərsiniz. 🚀\n\n"
                "**Botun fəaliyyəti:**\n"
                "✅ Tam avtomatlaşdırılmış bilet alışı\n"
                "✅ Təhlükəsiz Telegram Stars ödəniş sistemi\n"
                "✅ Şəffaf və anlıq təsdiq mesajları\n\n"
                "**Necə iştirak etməli?**\n"
                "Aşağıdakı menyudan bilet sayını seçin və ödənişi tamamlayın. "
                "Hər bilet cəmi **5 Ulduzdur.**"
            )
            
            reply_markup = {
                "keyboard": [
                    [{"text": "🎟 1 Bilet (5 ⭐)"}, {"text": "🎟 5 Bilet (25 ⭐)"}],
                    [{"text": "🎟 10 Bilet (50 ⭐)"}]
                ],
                "resize_keyboard": True
            }
            
            requests.post(url, json={
                "chat_id": chat_id, 
                "text": welcome_text,
                "parse_mode": "Markdown",
                "reply_markup": reply_markup
            })

        # 2. Düymələrə reaksiya (Bilet seçimi)
        elif "1 Bilet" in text:
            send_invoice(chat_id, 1)
        elif "5 Bilet" in text:
            send_invoice(chat_id, 5)
        elif "10 Bilet" in text:
            send_invoice(chat_id, 10)

        # 3. Ödəniş uğurlu olanda gələn təsdiq mesajı
        if "successful_payment" in update["message"]:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={
                              "chat_id": chat_id, 
                              "text": "✅ **Ödəniş qəbul edildi!**\n\nLotereyada iştirakınız uğurla təsdiqləndi. Uğurlar arzulayırıq!",
                              "parse_mode": "Markdown"
                          })

    # 4. Ödənişdən əvvəlki son yoxlanış (Vacibdir!)
    if "pre_checkout_query" in update:
        query_id = update["pre_checkout_query"]["id"]
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                      data={"pre_checkout_query_id": query_id, "ok": True})

    return "OK", 200
