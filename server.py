from quart import Quart, request, session, redirect, send_from_directory, jsonify
import asyncio
import json
import os
import secrets
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64

app = Quart(__name__)
app.secret_key = 'supersecretkey'

USERS_FILE = 'users.json'
CHAT_FILE = 'chat.json'
CAPTCHA_TEXT = ''

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)

if not os.path.exists(CHAT_FILE):
    with open(CHAT_FILE, 'w') as f:
        json.dump([], f)


@app.before_serving
async def init_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
    if not os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, 'w') as f:
            json.dump([], f)


@app.route('/')
async def index():
    return redirect('/reg.html')


@app.route('/reg.html')
async def reg_page():
    return await send_from_directory('.', 'reg.html')


@app.route('/chat.html')
async def chat_page():
    if 'username' not in session:
        return redirect('/reg.html')
    return await send_from_directory('.', 'chat.html')


@app.route('/generate_captcha')
async def generate_captcha():
    global CAPTCHA_TEXT
    CAPTCHA_TEXT = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(5))
    image = Image.new('RGB', (100, 40), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except:
        font = ImageFont.load_default()
    draw.text((10, 8), CAPTCHA_TEXT, font=font, fill=(0, 0, 0))

    buf = BytesIO()
    image.save(buf, format='PNG')
    data = base64.b64encode(buf.getvalue()).decode('utf-8')
    return jsonify({'captcha': data})


def load_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)


@app.route('/register', methods=['POST'])
async def register():
    data = await request.form
    username = data.get('username')
    password = data.get('password')
    captcha = data.get('captcha')

    if not all([username, password, captcha]):
        return 'Missing fields', 400
    if captcha.upper() != CAPTCHA_TEXT:
        return 'Invalid CAPTCHA', 400

    users = load_users()
    if username in users:
        return 'User already exists', 400

    users[username] = password
    save_users(users)
    session['username'] = username
    return redirect('/chat.html')


@app.route('/login', methods=['POST'])
async def login():
    data = await request.form
    username = data.get('username')
    password = data.get('password')
    captcha = data.get('captcha')

    if not all([username, password, captcha]):
        return 'Missing fields', 400
    if captcha.upper() != CAPTCHA_TEXT:
        return 'Invalid CAPTCHA', 400

    users = load_users()
    if username not in users or users[username] != password:
        return 'Invalid credentials', 401

    session['username'] = username
    return redirect('/chat.html')


@app.route('/send_message', methods=['POST'])
async def send_message():
    if 'username' not in session:
        return 'Unauthorized', 401

    data = await request.get_json()
    message = data.get('message')
    recipient = data.get('recipient')  # optional

    if not message:
        return 'Empty message', 400

    with open(CHAT_FILE, 'r') as f:
        chat = json.load(f)

    chat.append({
        'sender': session['username'],
        'message': message,
        'recipient': recipient
    })

    with open(CHAT_FILE, 'w') as f:
        json.dump(chat, f)

    return 'Message sent'


@app.route('/get_messages')
async def get_messages():
    if 'username' not in session:
        return 'Unauthorized', 401

    with open(CHAT_FILE, 'r') as f:
        chat = json.load(f)

    username = session['username']
    visible_messages = [msg for msg in chat if not msg.get('recipient') or msg.get('recipient') == username or msg['sender'] == username]

    return jsonify(visible_messages)


@app.route('/logout')
async def logout():
    session.clear()
    return redirect('/reg.html')


@app.route('/<path:path>')
async def serve_static(path):
    return await send_from_directory('.', path)


if __name__ == '__main__':
    app.run()
