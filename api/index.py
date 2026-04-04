import json
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"

def send_invoice(chat_id, count):
    price = count * 5  # Hər bilet 5 ulduz
    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
    payload = {
        "chat_id": chat_id,
        "title": f"Lotereya Bileti ({count} ədəd)",
        "description": "Uduşda iştirak üçün Stars ilə ödəniş edin.",
        "payload": "lottery_pay",
        "provider_token": "", 
        "currency": "XTR",
        "prices": json.dumps([{"label": "Bilet", "amount": price}])
    }
    requests.post(url, data=payload)

@app.route('/api', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if text == "/start":
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            menu = {
                "keyboard": [
                    [{"text": "🎟 1 Bilet Al (5 ⭐)"}, {"text": "🎟 5 Bilet Al (25 ⭐)"}]
                ],
                "resize_keyboard": True
            }
            requests.post(url, json={
                "chat_id": chat_id, 
                "text": "Xoş gəldiniz! Neçə bilet almaq istəyirsiniz?",
                "reply_markup": menu
            })

        elif "1 Bilet Al" in text:
            send_invoice(chat_id, 1)
        elif "5 Bilet Al" in text:
            send_invoice(chat_id, 5)

    # Ödənişdən əvvəlki son təsdiq (Vacibdir!)
    if "pre_checkout_query" in update:
        url = f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery"
        requests.post(url, data={"pre_checkout_query_id": update["pre_checkout_query"]["id"], "ok": True})

    # Ödəniş uğurla bitəndə
    if "message" in update and "successful_payment" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": chat_id, "text": "Təbriklər! Ödəniş uğurlu oldu, lotereyada iştirakınız təsdiqləndi!"})

    return "OK", 200
