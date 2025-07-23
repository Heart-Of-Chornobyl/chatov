from telegram.ext import ApplicationBuilder, CommandHandler
import os

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update, context):
    await update.message.reply_text("Привет! Бот работает.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.run_polling()

if __name__ == "__main__":
    main()
