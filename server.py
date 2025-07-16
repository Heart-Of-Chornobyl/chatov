import asyncio
import websockets
import base64

connected = set()

async def handler(websocket, path):
    connected.add(websocket)
    try:
        async for message in websocket:
            if message.startswith("FILE:"):
                # Формат: FILE:имя_файла:base64_данные
                _, filename, b64data = message.split(":", 2)
                with open(filename, "wb") as f:
                    f.write(base64.b64decode(b64data))
                # Отправить всем, кроме отправителя, уведомление о файле
                for conn in connected:
                    if conn != websocket:
                        await conn.send(f"Файл {filename} получен")
            else:
                # Переслать обычное сообщение всем остальным
                for conn in connected:
                    if conn != websocket:
                        await conn.send(message)
    finally:
        connected.remove(websocket)

async def main():
    print("Сервер запущен на ws://0.0.0.0:8765")
    async with websockets.serve(handler, "0.0.0.0", 443):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())