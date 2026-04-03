import os
import asyncio
import json
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import LabeledPrice, PreCheckoutQuery

# TOKEN hissəsinə BotFather-dən aldığınız kodu yazın
TOKEN = "TOKENI_BURA_YAPISDIRIN"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# 1. WebApp-dan gələn ulduz ödənişi istəyini tutmaq
@dp.message(F.web_app_data)
async def process_stars_order(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") == "buy_stars":
            await message.answer_invoice(
                title="Lotereya Bileti",
                description=f"{data['count']} ədəd bilet alışı",
                payload="lottery_purchase",
                currency="XTR", # Telegram Stars kodu
                prices=[LabeledPrice(label="Bilet", amount=data['total_price'])],
                provider_token="" # Stars üçün boş qalır
            )
    except Exception as e:
        print(f"Xəta: {e}")

# 2. Ödəniş öncəsi təsdiq (Pre-checkout) - Mütləqdir!
@dp.pre_checkout_query()
async def checkout_confirm(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

# 3. Ödəniş uğurlu olanda mesaj
@dp.message(F.successful_payment)
async def payment_done(message: types.Message):
    await message.answer("Təbriklər! Ödəniş uğurla tamamlandı. Biletiniz qeydə alındı! 🎫")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
