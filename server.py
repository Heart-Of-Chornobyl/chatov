from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_session import Session
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import random
import string
import os

app = Flask(__name__, template_folder='.')  # шаблоны — в той же папке
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secretkey123')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
Session(app)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# --- Модели базы ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    username = db.Column(db.String(50), nullable=False)
    text = db.Column(db.String(500), nullable=False)

# --- Создание таблиц при старте, если их нет ---
with app.app_context():
    db.create_all()

# --- Капча ---
def generate_captcha(length=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@app.route('/generate_captcha')
def generate_captcha_route():
    captcha = generate_captcha()
    session['captcha'] = captcha
    return jsonify({'captcha': captcha})

# --- Регистрация ---
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    captcha_input = data.get('captcha', '').strip().upper()
    captcha_session = session.get('captcha', '')

    if not username or not password or not captcha_input:
        return jsonify({'message': 'Все поля обязательны'}), 400

    if captcha_input != captcha_session:
        return jsonify({'message': 'Неверная капча'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Пользователь уже существует'}), 400

    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, password_hash=pw_hash)
    db.session.add(new_user)
    db.session.commit()

    session['username'] = username
    return jsonify({'message': 'Регистрация успешна'})

# --- Вход ---
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'message': 'Введите имя и пароль'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Неверное имя или пароль'}), 400

    session['username'] = username
    return jsonify({'message': 'Вход успешен'})

# --- Страницы ---
@app.route('/')
def index():
    if 'username' in session:
        return redirect('/chat.html')
    else:
        return redirect('/reg.html')

@app.route('/reg')
def reg_page():
    return render_template('reg.html')

@app.route('/chat.html')
def chat_page():
    if 'username' not in session:
        return redirect('/reg.html')
    return render_template('chat.html')

# --- Сообщения ---

@socketio.on('connect')
def on_connect():
    if 'username' not in session:
        return False  # разорвать соединение если не авторизован
    # При подключении отправляем последние 50 сообщений
    messages = Message.query.order_by(Message.id.desc()).limit(50).all()
    msgs = [{'user': m.username, 'text': m.text} for m in reversed(messages)]
    emit('load_messages', msgs)

@socketio.on('send_message')
def handle_message(data):
    if 'username' not in session:
        return
    text = data.get('text', '').strip()
    if not text:
        return
    username = session['username']
    user = User.query.filter_by(username=username).first()
    if not user:
        return

    msg = Message(user_id=user.id, username=username, text=text)
    db.session.add(msg)
    db.session.commit()

    emit('new_message', {'user': username, 'text': text}, broadcast=True)

# --- Выход ---
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/reg.html')

if __name__ == '__main__':
    # При запуске локально (для dev)
    socketio.run(app, host='0.0.0.0', port=5000)
