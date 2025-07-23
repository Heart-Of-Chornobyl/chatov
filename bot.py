import os
import replicate
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from googletrans import Translator
import aiohttp

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
REPLICATE_TOKEN = os.getenv("REPLICATE_TOKEN")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)
translator = Translator()

# Тексты для разных языков
texts = {
    "en": {
        "greeting": "👋 Hello! I'm your photo enhancer bot. Choose an option:",
        "menu": "📌 Main menu:",
        "btn_improve": "📸 Enhance Photo",
        "btn_help": "❓ Help",
        "btn_about": "ℹ About",
        "help": "Send me a photo, and I will enhance it using AI.",
        "about": "I am a bot that improves photo quality using AI models.",
        "processing": "⏳ Processing your photo...",
        "done": "✅ Here is your enhanced photo!",
        "error": "❌ Something went wrong."
    },
    "uk": {
        "greeting": "👋 Привіт! Я бот для покращення фото. Обери опцію:",
        "menu": "📌 Головне меню:",
        "btn_improve": "📸 Покращити фото",
        "btn_help": "❓ Допомога",
        "btn_about": "ℹ Про бота",
        "help": "Надішли мені фото, і я покращу його за допомогою AI.",
        "about": "Я бот, що покращує якість зображень за допомогою AI.",
        "processing": "⏳ Обробляю твоє фото...",
        "done": "✅ Ось твоє покращене фото!",
        "error": "❌ Щось пішло не так."
    },
    "ru": {
        "greeting": "👋 Привет! Я бот для улучшения фото. Выбери опцию:",
        "menu": "📌 Главное меню:",
        "btn_improve": "📸 Улучшить фото",
        "btn_help": "❓ Помощь",
        "btn_about": "ℹ О боте",
        "help": "Отправь мне фото, и я улучшу его с помощью AI.",
        "about": "Я бот, который улучшает фото с помощью AI.",
        "processing": "⏳ Обрабатываю фото...",
        "done": "✅ Вот твоё улучшенное фото!",
        "error": "❌ Что-то пошло не так."
    },
    "pl": {
        "greeting": "👋 Cześć! Jestem botem do poprawy zdjęć. Wybierz opcję:",
        "menu": "📌 Główne menu:",
        "btn_improve": "📸 Popraw zdjęcie",
        "btn_help": "❓ Pomoc",
        "btn_about": "ℹ O bocie",
        "help": "Wyślij mi zdjęcie, a poprawię je za pomocą AI.",
        "about": "Jestem botem, który poprawia zdjęcia dzięki AI.",
        "processing": "⏳ Przetwarzam zdjęcie...",
        "done": "✅ Oto twoje ulepszone zdjęcie!",
        "error": "❌ Coś poszło nie tak."
    },
    "cs": {
        "greeting": "👋 Ahoj! Jsem bot na vylepšení fotek. Vyber možnost:",
        "menu": "📌 Hlavní menu:",
        "btn_improve": "📸 Vylepšit fotku",
        "btn_help": "❓ Nápověda",
        "btn_about": "ℹ O botovi",
        "help": "Pošli mi fotku a vylepším ji pomocí AI.",
        "about": "Jsem bot, který vylepšuje fotky pomocí AI.",
        "processing": "⏳ Zpracovávám fotku...",
        "done": "✅ Tady je tvoje vylepšená fotka!",
        "error": "❌ Něco se pokazilo."
    },
    "de": {
        "greeting": "👋 Hallo! Ich bin ein Bot zur Fotoverbesserung. Wähle eine Option:",
        "menu": "📌 Hauptmenü:",
        "btn_improve": "📸 Foto verbessern",
        "btn_help": "❓ Hilfe",
        "btn_about": "ℹ Über Bot",
        "help": "Schick mir ein Foto und ich verbessere es mit KI.",
        "about": "Ich bin ein Bot, der Fotos mit KI verbessert.",
        "processing": "⏳ Verarbeite dein Foto...",
        "done": "✅ Hier ist dein verbessertes Foto!",
        "error": "❌ Etwas ist schiefgelaufen."
    }
}

def get_text(lang, key):
    return texts.get(lang, texts["en"]).get(key, key)

def get_menu(lang):
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton(get_text(lang, "btn_improve"), callback_data="improve"),
        InlineKeyboardButton(get_text(lang, "btn_help"), callback_data="help"),
        InlineKeyboardButton(get_text(lang, "btn_about"), callback_data="about")
    )

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    lang = message.from_user.language_code if message.from_user.language_code else "en"
    await message.answer(get_text(lang, "greeting"), reply_markup=get_menu(lang))

@dp.callback_query_handler(lambda c: c.data in ["help", "about", "improve"])
async def menu_callback(callback_query: types.CallbackQuery):
    lang = callback_query.from_user.language_code if callback_query.from_user.language_code else "en"

    if callback_query.data == "help":
        await callback_query.message.edit_text(get_text(lang, "help"), reply_markup=get_menu(lang))
    elif callback_query.data == "about":
        await callback_query.message.edit_text(get_text(lang, "about"), reply_markup=get_menu(lang))
    elif callback_query.data == "improve":
        await callback_query.message.edit_text(get_text(lang, "menu") + "\n📸 " + get_text(lang, "btn_improve"),
                                               reply_markup=get_menu(lang))

@dp.message_handler(content_types=["photo"])
async def handle_photo(message: types.Message):
    lang = message.from_user.language_code if message.from_user.language_code else "en"
    await message.answer(get_text(lang, "processing"))

    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                img_bytes = await resp.read()

        img_path = "temp.jpg"
        with open(img_path, "wb") as f:
            f.write(img_bytes)

        client = replicate.Client(api_token=REPLICATE_TOKEN)
        output = client.run(
            "tencentarc/gfpgan:latest",
            input={"img": open(img_path, "rb")}
        )

        improved_img_url = output[0]
        await message.answer_photo(improved_img_url, caption=get_text(lang, "done"), reply_markup=get_menu(lang))

    except Exception as e:
        await message.answer(get_text(lang, "error"))
        print(e)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
