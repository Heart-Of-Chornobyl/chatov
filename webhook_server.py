from aiohttp import web
import asyncio
import os
from bot import dp
from aiogram import Bot

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

async def handle(request):
    return web.Response(text="Бот работает через Render ✅")

async def on_startup(app):
    asyncio.create_task(dp.start_polling())

app = web.Application()
app.router.add_get("/", handle)
app.on_startup.append(on_startup)
