import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from googletrans import Translator
import replicate

# Логирование
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN not set in environment!")

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}{WEBHOOK_PATH}"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8000))

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)
translator = Translator()

# Команда /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("👋 Привет! Я Magic Face Bot. Отправь мне текст, и я переведу его на английский.")

# Перевод текста
@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def translate_text(message: types.Message):
    translated = translator.translate(message.text, dest="en")
    await message.answer(f"🔤 Перевод: <b>{translated.text}</b>")

# Обработка изображений через Replicate (пример)
@dp.message_handler(content_types=types.ContentTypes.PHOTO)
async def process_image(message: types.Message):
    await message.answer("🖼 Обрабатываю изображение...")
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_path = file_info.file_path
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    output = replicate.run(
        "stability-ai/stable-diffusion:db21e45d3f46df3f9a8096dcf44b4f26c47b9a6f76d70a1e87175e6f3cf02e32",
        input={"image": file_url, "prompt": "Make it more magical"}
    )
    await message.answer(f"✅ Результат: {output}")

# Webhook init
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook set to {WEBHOOK_URL}")

async def on_shutdown(dp):
    await bot.delete_webhook()
    logging.info("Webhook deleted")

# Создаём aiohttp приложение
app = web.Application()
app.router.add_get("/", lambda request: web.Response(text="Bot is running"))
app.router.add_post(WEBHOOK_PATH, lambda request: dp.feed_webhook_update(request))

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
