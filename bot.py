import os
import replicate
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from googletrans import Translator

# Получаем токены из окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
REPLICATE_TOKEN = os.getenv("REPLICATE_TOKEN")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
translator = Translator()

# Словарь переводов для популярных языков
texts = {
    "en": {
        "greeting": "Hello! 👋\nSend me a photo to improve it or use the menu below.",
        "processing": "Processing your photo...",
        "done": "Here is your improved photo! ✅",
        "error": "Something went wrong. ❌",
        "menu": "Choose an option:",
        "btn_send": "🖼 Send Photo",
        "btn_lang": "🌍 Change Language",
        "btn_info": "ℹ Info",
        "choose_lang": "Select your language:",
        "info": "I use AI to enhance your photos!"
    },
    "uk": {
        "greeting": "Привіт! 👋\nНадішли фото для покращення або скористайся меню нижче.",
        "processing": "Обробляю твоє фото...",
        "done": "Ось твоє покращене фото! ✅",
        "error": "Щось пішло не так. ❌",
        "menu": "Вибери опцію:",
        "btn_send": "🖼 Надіслати фото",
        "btn_lang": "🌍 Змінити мову",
        "btn_info": "ℹ Інформація",
        "choose_lang": "Вибери мову:",
        "info": "Я використовую AI для покращення фото!"
    },
    "ru": {
        "greeting": "Привет! 👋\nОтправь фото для улучшения или воспользуйся меню ниже.",
        "processing": "Обрабатываю фото...",
        "done": "Вот твоё улучшенное фото! ✅",
        "error": "Что-то пошло не так. ❌",
        "menu": "Выбери опцию:",
        "btn_send": "🖼 Отправить фото",
        "btn_lang": "🌍 Сменить язык",
        "btn_info": "ℹ Инфо",
        "choose_lang": "Выбери язык:",
        "info": "Я использую AI для улучшения фото!"
    },
    "pl": {
        "greeting": "Cześć! 👋\nWyślij zdjęcie do poprawy lub użyj menu poniżej.",
        "processing": "Przetwarzam twoje zdjęcie...",
        "done": "Oto twoje ulepszone zdjęcie! ✅",
        "error": "Coś poszło nie tak. ❌",
        "menu": "Wybierz opcję:",
        "btn_send": "🖼 Wyślij zdjęcie",
        "btn_lang": "🌍 Zmień język",
        "btn_info": "ℹ Info",
        "choose_lang": "Wybierz język:",
        "info": "Używam AI do ulepszania zdjęć!"
    },
    "de": {
        "greeting": "Hallo! 👋\nSchick mir ein Foto oder nutze das Menü unten.",
        "processing": "Verarbeite dein Foto...",
        "done": "Hier ist dein verbessertes Foto! ✅",
        "error": "Etwas ist schiefgelaufen. ❌",
        "menu": "Wähle eine Option:",
        "btn_send": "🖼 Foto senden",
        "btn_lang": "🌍 Sprache ändern",
        "btn_info": "ℹ Info",
        "choose_lang": "Wähle deine Sprache:",
        "info": "Ich nutze KI, um deine Fotos zu verbessern!"
    }
}

# Память для выбранных языков
user_lang = {}

def get_text(user_id, key, fallback="en"):
    lang = user_lang.get(user_id, fallback)
    return texts.get(lang, texts["en"]).get(key, key)

# Главное меню
def main_menu(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, "btn_send"), callback_data="send_photo")],
        [InlineKeyboardButton(text=get_text(user_id, "btn_lang"), callback_data="change_lang")],
        [InlineKeyboardButton(text=get_text(user_id, "btn_info"), callback_data="info")]
    ])

# Выбор языка
def language_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_uk")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇵🇱 Polski", callback_data="lang_pl")],
        [InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de")]
    ])

# Старт
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    lang = message.from_user.language_code or "en"
    if lang not in texts:
        lang = "en"
    user_lang[message.from_user.id] = lang
    await message.answer(get_text(message.from_user.id, "greeting"), reply_markup=main_menu(message.from_user.id))

# Обработка колбэков меню
@dp.callback_query(F.data == "change_lang")
async def change_language(callback: types.CallbackQuery):
    await callback.message.edit_text(get_text(callback.from_user.id, "choose_lang"), reply_markup=language_menu())

@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[1]
    user_lang[callback.from_user.id] = lang_code
    await callback.message.edit_text(get_text(callback.from_user.id, "greeting"), reply_markup=main_menu(callback.from_user.id))

@dp.callback_query(F.data == "info")
async def info_cmd(callback: types.CallbackQuery):
    await callback.answer(get_text(callback.from_user.id, "info"), show_alert=True)

# Приём фото
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await message.answer(get_text(message.from_user.id, "processing"))

    # Получаем фото
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"

    try:
        # Скачиваем фото
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                img_bytes = await resp.read()

        # Сохраняем временно
        img_path = "temp.jpg"
        with open(img_path, "wb") as f:
            f.write(img_bytes)

        # Обрабатываем через Replicate
        client = replicate.Client(api_token=REPLICATE_TOKEN)
        output = client.run(
            "tencentarc/gfpgan:latest",
            input={"img": open(img_path, "rb")}
        )

        improved_img_url = output[0]
        await message.answer_photo(improved_img_url, caption=get_text(message.from_user.id, "done"))
    except Exception as e:
        await message.answer(get_text(message.from_user.id, "error"))
        print(e)

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
