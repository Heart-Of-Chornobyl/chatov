from flask import Flask, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import sqlite3
import os
import random
import string

app = Flask(__name__, static_url_path='', static_folder='.')
app.secret_key = 'секретный_ключ'
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_FILE = 'database.db'

# === База данных ===
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                text TEXT NOT NULL
            )
        ''')

init_db()  # создать таблицы при запуске

# === Капча ===
@app.route('/generate_captcha')
def generate_captcha():
    captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    session['captcha'] = captcha
    return jsonify({'captcha': captcha})

# === Регистрация ===
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

    try:
        with get_db() as db:
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        session['username'] = username
        return jsonify({'message': 'Регистрация успешна'})
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Пользователь уже существует'}), 400

# === Вход ===
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    with get_db() as db:
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        if user:
            session['username'] = username
            return jsonify({'message': 'Вход выполнен'})
        else:
            return jsonify({'message': 'Неверные данные'}), 400

# === HTML-страницы ===
@app.route('/')
def root():
    return send_from_directory('.', 'reg.html')

@app.route('/chat.html')
def chat_page():
    return send_from_directory('.', 'chat.html')

# === WebSocket ===
@socketio.on('connect')
def on_connect():
    if 'username' not in session:
        return False  # отклонить соединение
    with get_db() as db:
        msgs = db.execute('SELECT username, text FROM messages ORDER BY id ASC').fetchall()
    emit('load_messages', [{'user': row['username'], 'text': row['text']} for row in msgs])

@socketio.on('send_message')
def on_message(data):
    username = session.get('username', 'Аноним')
    text = data.get('text', '').strip()
    if not text:
        return
    with get_db() as db:
        db.execute('INSERT INTO messages (username, text) VALUES (?, ?)', (username, text))
    emit('new_message', {'user': username, 'text': text}, broadcast=True)

# === Запуск ===
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)
