import os
import asyncio
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update, context):
    await update.message.reply_text("Привет! Бот работает.")

async def main():
    # Создаём приложение напрямую, без ApplicationBuilder
    app = Application(token=BOT_TOKEN)

    app.add_handler(CommandHandler("start", start))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
