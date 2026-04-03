import os
import json
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types

TOKEN = "8207828317:AAFub6sP6uoLWTcjydq2qybviAuaWTARA_o"
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

async def handle_update(update_data):
    update = types.Update.model_validate(update_data, context={"bot": bot})
    
    # WebApp-dan gələn məlumatı tuturuq
    if update.message and update.message.web_app_data:
        data = json.loads(update.message.web_app_data.data)
        if data.get("action") == "buy_stars":
            await bot.send_invoice(
                chat_id=update.message.chat.id,
                title="Lotereya Bileti",
                description=f"{data['count']} ədəd bilet",
                payload="lottery_pay",
                currency="XTR",
                prices=[types.LabeledPrice(label="Bilet", amount=data['total_price'])],
                provider_token=""
            )

    # Ödəniş təsdiqi
    if update.pre_checkout_query:
        await bot.answer_pre_checkout_query(update.pre_checkout_query.id, ok=True)

    # Uğurlu ödəniş mesajı
    if update.message and update.message.successful_payment:
        await bot.send_message(update.message.chat.id, "Təbriklər! Ödəniş uğurla tamamlandı! 🎫")

@app.route('/api', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update_data = request.json
        asyncio.run(handle_update(update_data))
        return "OK", 200
    return "Method Not Allowed", 405
