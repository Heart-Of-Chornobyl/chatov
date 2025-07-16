from flask import Flask, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import json
import random
import string

app = Flask(__name__, static_url_path='', static_folder='.')
app.secret_key = 'секретный_ключ'
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'

# Загрузка пользователей и сообщений
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def load_messages():
    if not os.path.exists(MESSAGES_FILE):
        return []
    with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_messages(messages):
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

# Генерация капчи
@app.route('/generate_captcha')
def generate_captcha():
    captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    session['captcha'] = captcha
    return jsonify({'captcha': captcha})

# Регистрация
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    captcha = data.get('captcha', '').strip()
    if not username or not password or not captcha:
        return jsonify({'message': 'Заполните все поля'}), 400
    if captcha != session.get('captcha'):
        return jsonify({'message': 'Неверная капча'}), 400

    users = load_users()
    if username in users:
        return jsonify({'message': 'Пользователь уже существует'}), 400
    users[username] = {'password': password}
    save_users(users)
    session['username'] = username
    return jsonify({'message': 'Регистрация успешна'})

# Вход
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    users = load_users()
    if username not in users or users[username]['password'] != password:
        return jsonify({'message': 'Неверные данные'}), 400
    session['username'] = username
    return jsonify({'message': 'Вход выполнен'})

# Отдача HTML-файлов
@app.route('/')
def root():
    return send_from_directory('.', 'reg.html')

@app.route('/chat.html')
def chat_page():
    return send_from_directory('.', 'chat.html')

# Socket.IO чат
@socketio.on('connect')
def handle_connect():
    if 'username' not in session:
        return False  # отключить сокет, если не вошел
    emit('load_messages', load_messages())

@socketio.on('send_message')
def handle_send(data):
    username = session.get('username', 'Аноним')
    text = data.get('text', '').strip()
    if not text:
        return

    message = {'user': username, 'text': text}
    messages = load_messages()
    messages.append(message)
    if len(messages) > 100:
        messages = messages[-100:]
    save_messages(messages)

    emit('new_message', message, broadcast=True)

# Запуск
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)
