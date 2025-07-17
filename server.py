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

POSTGRES_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@host:port/dbname')

app.config['SQLALCHEMY_DATABASE_URI'] = POSTGRES_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_PERMANENT'] = False

db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db
sess = Session(app)

CORS(app, supports_credentials=True)
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
    sender = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    # Для личного сообщения: получатель, иначе None для публичного
    recipient = db.Column(db.String(100), nullable=True)

# --- Капча ---

def generate_captcha_text(length=5):
    letters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(letters, k=length))

@app.route('/generate_captcha')
def generate_captcha():
    captcha = generate_captcha_text()
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
        return jsonify({'message': 'Все поля обязательны'}), 400

    if captcha.upper() != session.get('captcha', '').upper():
        return jsonify({'message': 'Неверная капча'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Пользователь уже существует'}), 400

    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    session['username'] = username

    return jsonify({'message': 'Регистрация успешна'}), 200

# --- Вход ---

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'message': 'Все поля обязательны'}), 400

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Неверное имя пользователя или пароль'}), 400

    session['username'] = username

    return jsonify({'message': 'Вход успешен'}), 200

# --- Выход ---

@app.route('/logout')
def logout():
    session.pop('username', None)
    return jsonify({'message': 'Выход выполнен'}), 200

# --- Чат ---

@socketio.on('connect')
def on_connect():
    if 'username' not in session:
        return False

    # Отправляем все публичные и личные сообщения этого пользователя
    username = session['username']
    msgs = Message.query.filter(
        (Message.recipient == None) |  # публичные
        (Message.sender == username) | # личные от пользователя
        (Message.recipient == username) # личные ему
    ).order_by(Message.id.asc()).all()

    msgs_list = []
    for m in msgs:
        msgs_list.append({
            'sender': m.sender,
            'text': m.text,
            'recipient': m.recipient  # None — публичное, иначе ник получателя
        })
    emit('load_messages', msgs_list)

@socketio.on('send_message')
def on_send_message(data):
    if 'username' not in session:
        return

    text = data.get('text', '').strip()
    recipient = data.get('recipient')  # ник получателя или null/None
    user = session['username']

    if not text:
        return

    # Проверим, если recipient задан, то он должен быть в базе
    if recipient:
        recipient_user = User.query.filter_by(username=recipient).first()
        if recipient_user is None:
            return  # invalid recipient — игнорируем

    msg = Message(sender=user, text=text, recipient=recipient)
    db.session.add(msg)
    db.session.commit()

    # Отправляем сообщение всем, кто должен его видеть
    # Публичное — всем, личное — только отправителю и получателю

    msg_data = {'sender': user, 'text': text, 'recipient': recipient}

    if recipient:
        # Отправляем только двум юзерам
        emit('new_message', msg_data, room=user)
        emit('new_message', msg_data, room=recipient)
    else:
        # Публичное — всем
        emit('new_message', msg_data, broadcast=True)

@socketio.on('join')
def on_join(data):
    if 'username' not in session:
        return
    username = session['username']
    join_room(username)  # каждый пользователь — в своей комнате

@socketio.on('leave')
def on_leave(data):
    if 'username' not in session:
        return
    username = session['username']
    leave_room(username)

# --- Запуск и создание таблиц ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=10000)
