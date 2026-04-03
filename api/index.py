import os
import json
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import LabeledPrice, PreCheckoutQuery

# TOKEN-i bura yapışdırın (BotFather-dən aldığınız)
TOKEN = "BOT_TOKENINIZI_BURA_YAZIN"
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

@dp.message(F.web_app_data)
async def process_stars_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    if data.get("action") == "buy_stars":
        await message.answer_invoice(
            title="Lotereya Bileti",
            description=f"{data['count']} ədəd bilet",
            payload="lottery_purchase",
            currency="XTR", 
            prices=[LabeledPrice(label="Stars", amount=data['total_price'])],
            provider_token=""
        )

@dp.pre_checkout_query()
async def checkout_confirm(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def payment_done(message: types.Message):
    await message.answer("Təbriklər! Ödəniş uğurla tamamlandı. 🎫")

@app.route('/', methods=['POST'])
def webhook():
    update = types.Update.model_validate(request.json, context={"bot": bot})
    asyncio.run(dp.feed_update(bot, update))
    return "OK", 200
