import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.executor import start_webhook
from googletrans import Translator
import aiohttp
import replicate

# Токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
REPLICATE_TOKEN = os.getenv("REPLICATE_TOKEN")

# Webhook settings
WEBHOOK_HOST = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Server settings
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 5000))

# Init
bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())
translator = Translator()

logging.basicConfig(level=logging.INFO)

# Тексты
texts = {
    "en": {"greeting": "Hello! Send me a photo to improve it.", "processing": "Processing...", "done": "Here is your improved photo!", "error": "Something went wrong."},
    "uk": {"greeting": "Привіт! Надішли фото для покращення.", "processing": "Обробка...", "done": "Ось твоє покращене фото!", "error": "Щось пішло не так."},
    "ru": {"greeting": "Привет! Отправь фото для улучшения.", "processing": "Обрабатываю...", "done": "Вот твоё улучшенное фото!", "error": "Что-то пошло не так."}
}

def get_text(lang, key):
    return texts.get(lang, texts["en"]).get(key, texts["en"][key])

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    lang = message.from_user.language_code if message.from_user.language_code else "en"
    await message.answer(get_text(lang, "greeting"))

@dp.message_handler(content_types=["photo"])
async def handle_photo(message: types.Message):
    lang = message.from_user.language_code if message.from_user.language_code else "en"
    await message.answer(get_text(lang, "processing"))

    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"

        # Download photo
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                img_bytes = await resp.read()

        img_path = "temp.jpg"
        with open(img_path, "wb") as f:
            f.write(img_bytes)

        # Process image
        client = replicate.Client(api_token=REPLICATE_TOKEN)
        output = client.run("tencentarc/gfpgan:latest", input={"img": open(img_path, "rb")})
        improved_img_url = output[0]

        await message.answer_photo(improved_img_url, caption=get_text(lang, "done"))

    except Exception as e:
        await message.answer(get_text(lang, "error"))
        print(e)

async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    logging.warning("Shutting down..")
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
    logging.warning("Bye!")

if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT
    )
