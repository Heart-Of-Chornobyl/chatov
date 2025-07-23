import os
import replicate
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from googletrans import Translator
import aiohttp

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
REPLICATE_TOKEN = os.getenv("REPLICATE_TOKEN")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)
translator = Translator()

# Словарь переводов для популярных языков
texts = {
    "en": {
        "greeting": "Hello! Send me a photo to improve it.",
        "processing": "Processing your photo...",
        "done": "Here is your improved photo!",
        "error": "Something went wrong."
    },
    "uk": {
        "greeting": "Привіт! Надішли мені фото для покращення.",
        "processing": "Обробляю твоє фото...",
        "done": "Ось твоє покращене фото!",
        "error": "Щось пішло не так."
    },
    "ru": {
        "greeting": "Привет! Отправь мне фото для улучшения.",
        "processing": "Обрабатываю твоё фото...",
        "done": "Вот твоё улучшенное фото!",
        "error": "Что-то пошло не так."
    },
    "pl": {
        "greeting": "Cześć! Wyślij mi zdjęcie do poprawy.",
        "processing": "Przetwarzam twoje zdjęcie...",
        "done": "Oto twoje ulepszone zdjęcie!",
        "error": "Coś poszło nie tak."
    },
    "cs": {
        "greeting": "Ahoj! Pošli mi fotku na vylepšení.",
        "processing": "Zpracovávám tvoji fotku...",
        "done": "Tady je tvoje vylepšená fotka!",
        "error": "Něco se pokazilo."
    },
    "de": {
        "greeting": "Hallo! Schick mir ein Foto zur Verbesserung.",
        "processing": "Verarbeite dein Foto...",
        "done": "Hier ist dein verbessertes Foto!",
        "error": "Etwas ist schiefgelaufen."
    }
}

# Функция для выбора текста
def get_text(lang_code, key):
    if lang_code in texts:
        return texts[lang_code][key]
    try:
        translated = translator.translate(texts["en"][key], dest=lang_code)
        return translated.text
    except:
        return texts["en"][key]

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    lang = message.from_user.language_code if message.from_user.language_code else "en"
    await message.answer(get_text(lang, "greeting"))

@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    lang = message.from_user.language_code if message.from_user.language_code else "en"
    await message.answer(get_text(lang, "processing"))

    # Получаем фото от пользователя
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

        # Отправляем улучшенное фото
        improved_img_url = output[0]
        await message.answer_photo(improved_img_url, caption=get_text(lang, "done"))

    except Exception as e:
        await message.answer(get_text(lang, "error"))
        print(e)

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
