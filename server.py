from flask import Flask, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import json
import random
import string
import sqlite3

app = Flask(__name__, static_url_path='', static_folder='.')
app.secret_key = 'секретный_ключ'
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

MESSAGES_FILE = 'messages.json'

# --- Работа с SQLite ---

def init_db():
    with sqlite3.connect('database.db') as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        db.commit()

def get_db():
    db = sqlite3.connect('database.db')
    db.row_factory = sqlite3.Row
    return db

# --- Сообщения в JSON файле ---

def load_messages():
    if not os.path.exists(MESSAGES_FILE):
        return []
    with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_messages(messages):
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

# --- Капча ---

@app.route('/generate_captcha')
def generate_captcha():
    captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    session['captcha'] = captcha
    return jsonify({'captcha': captcha})

# --- Регистрация ---

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

    db = get_db()
    cursor = db.execute('SELECT id FROM users WHERE username = ?', (username,))
    if cursor.fetchone():
        return jsonify({'message': 'Пользователь уже существует'}), 400

    db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
    db.commit()
    session['username'] = username
    return jsonify({'message': 'Регистрация успешна'})

# --- Вход ---

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    db = get_db()
    cursor = db.execute('SELECT password FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    if not row or row['password'] != password:
        return jsonify({'message': 'Неверные данные'}), 400
    session['username'] = username
    return jsonify({'message': 'Вход выполнен'})

# --- Статические страницы ---

@app.route('/')
def root():
    return send_from_directory('.', 'reg.html')

@app.route('/chat.html')
def chat_page():
    return send_from_directory('.', 'chat.html')

# --- Socket.IO чат ---

@socketio.on('connect')
def handle_connect():
    if 'username' not in session:
        return False  # Отключить если не залогинен
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

# --- Запуск ---

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=10000)
