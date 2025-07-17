from flask import Flask, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import sqlite3
import os
import random
import string
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room

# --- Конфигурация ---

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'замени_на_сложный_секрет')

# Используй здесь свою строку подключения к Postgres (например, из Render)
POSTGRES_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@host:port/dbname')

app.config['SQLALCHEMY_DATABASE_URI'] = POSTGRES_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Настройки сессий: сохранять в базе через SQLAlchemy
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_PERMANENT'] = False

# --- Инициализация ---

db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db
sess = Session(app)

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
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False)

# --- Модели БД ---

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)

# Таблица sessions создастся автоматически Flask-Session через SQLAlchemy

# --- Капча (простая) ---

def generate_captcha_text(length=5):
    letters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(letters, k=length))

@app.route('/generate_captcha')
def generate_captcha():
    captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    captcha = generate_captcha_text()
    session['captcha'] = captcha
    return jsonify({'captcha': captcha})

# === Регистрация ===
# --- Регистрация ---

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
@@ -54,61 +72,80 @@ def register():
    captcha = data.get('captcha', '').strip()

    if not username or not password or not captcha:
        return jsonify({'message': 'Заполните все поля'}), 400
    if captcha != session.get('captcha'):
        return jsonify({'message': 'Все поля обязательны'}), 400

    if captcha.upper() != session.get('captcha', '').upper():
        return jsonify({'message': 'Неверная капча'}), 400

    try:
        with get_db() as db:
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        session['username'] = username
        return jsonify({'message': 'Регистрация успешна'})
    except sqlite3.IntegrityError:
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Пользователь уже существует'}), 400

# === Вход ===
    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    session['username'] = username  # сохраняем в сессии

    return jsonify({'message': 'Регистрация успешна'}), 200

# --- Вход ---

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
    if not username or not password:
        return jsonify({'message': 'Все поля обязательны'}), 400

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Неверное имя пользователя или пароль'}), 400

    session['username'] = username

# === HTML-страницы ===
@app.route('/')
def root():
    return send_from_directory('.', 'reg.html')
    return jsonify({'message': 'Вход успешен'}), 200

@app.route('/chat.html')
def chat_page():
    return send_from_directory('.', 'chat.html')
# --- Выход ---

@app.route('/logout')
def logout():
    session.pop('username', None)
    return jsonify({'message': 'Выход выполнен'}), 200

# --- Чат ---

# === WebSocket ===
@socketio.on('connect')
def on_connect():
    if 'username' not in session:
        return False  # отклонить соединение
    with get_db() as db:
        msgs = db.execute('SELECT username, text FROM messages ORDER BY id ASC').fetchall()
    emit('load_messages', [{'user': row['username'], 'text': row['text']} for row in msgs])
        return False  # запретить соединение, если не залогинен

    # Отправить все старые сообщения
    msgs = Message.query.order_by(Message.id.asc()).all()
    msgs_list = [{'user': m.user, 'text': m.text} for m in msgs]
    emit('load_messages', msgs_list)

@socketio.on('send_message')
def on_message(data):
    username = session.get('username', 'Аноним')
def on_send_message(data):
    if 'username' not in session:
        return  # если нет сессии - игнорируем

    text = data.get('text', '').strip()
    if not text:
        return
    with get_db() as db:
        db.execute('INSERT INTO messages (username, text) VALUES (?, ?)', (username, text))
    emit('new_message', {'user': username, 'text': text}, broadcast=True)

# === Запуск ===
    user = session['username']
    msg = Message(user=user, text=text)
    db.session.add(msg)
    db.session.commit()

    emit('new_message', {'user': user, 'text': text}, broadcast=True)

# --- Запуск и создание таблиц ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # создаём таблицы, если ещё нет
    socketio.run(app, host='0.0.0.0', port=10000)
