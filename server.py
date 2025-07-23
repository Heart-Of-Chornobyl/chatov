import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import replicate

# Tokens
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
REPLICATE_TOKEN = os.getenv("REPLICATE_TOKEN")

WEBHOOK_HOST = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

texts = {
    "en": {"greeting": "Hello! Send me a photo to improve it.", "processing": "Processing...", "done": "Here is your improved photo!", "error": "Something went wrong."},
    "uk": {"greeting": "Привіт! Надішли фото для покращення.", "processing": "Обробка...", "done": "Ось твоє покращене фото!", "error": "Щось пішло не так."},
    "ru": {"greeting": "Привет! Отправь фото для улучшения.", "processing": "Обрабатываю...", "done": "Вот твоё улучшенное фото!", "error": "Что-то пошло не так."}
}

def get_text(lang, key):
    return texts.get(lang, texts["en"]).get(key, texts["en"][key])

@dp.message(commands=["start"])
async def start_cmd(message: types.Message):
    lang = message.from_user.language_code or "en"
    await message.answer(get_text(lang, "greeting"))

@dp.message(content_types=["photo"])
async def handle_photo(message: types.Message):
    lang = message.from_user.language_code or "en"
    await message.answer(get_text(lang, "processing"))

    try:
        file_info = await bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"

        # Обработка фото через Replicate
        client = replicate.Client(api_token=REPLICATE_TOKEN)
        output = client.run("tencentarc/gfpgan:latest", input={"img": file_url})
        improved_img_url = output[0]

        await message.answer_photo(improved_img_url, caption=get_text(lang, "done"))

    except Exception as e:
        await message.answer(get_text(lang, "error"))
        logging.error(e)

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

# Aiohttp app
app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
setup_application(app, dp, on_startup=on_startup, on_shutdown=on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
