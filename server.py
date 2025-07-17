import os
import random
import string
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'секретный_ключ_замени')

# Строка подключения к PostgreSQL (лучше в Render хранить в DATABASE_URL)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://chat_db_6jqp_user:N89VOuIv1nDWhsSE6mTuIFYNarI4LyVx@dpg-d1s4c8ngi27c73dm04t0-a.oregon-postgres.render.com/chat_db_6jqp'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Настройки сессии
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = SQLAlchemy(app)
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_PERMANENT'] = False
Session(app)

db = app.config['SESSION_SQLALCHEMY']

# Модели

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

# Инициализация SocketIO
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

# Капча
def generate_captcha_text(length=5):
    letters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(letters, k=length))

@app.route('/generate_captcha')
def generate_captcha():
    captcha = generate_captcha_text()
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

# Вход
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'message': 'Все поля обязательны'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Неверное имя пользователя или пароль'}), 400

    session['username'] = username
    return jsonify({'message': 'Вход успешен'}), 200

# Выход
@app.route('/logout')
def logout():
    session.pop('username', None)
    return jsonify({'message': 'Выход выполнен'}), 200

# Страницы
@app.route('/')
def index():
    return send_from_directory('.', 'reg.html')

@app.route('/chat.html')
def chat_page():
    return send_from_directory('.', 'chat.html')

# WebSocket

@socketio.on('connect')
def on_connect():
    if 'username' not in session:
        return False  # запретить подключение

    msgs = Message.query.order_by(Message.id.asc()).all()
    msgs_list = [{'user': m.user, 'text': m.text} for m in msgs]
    emit('load_messages', msgs_list)

@socketio.on('send_message')
def on_send_message(data):
    if 'username' not in session:
        return

    text = data.get('text', '').strip()
    if not text:
        return

    user = session['username']
    msg = Message(user=user, text=text)
    db.session.add(msg)
    db.session.commit()

    emit('new_message', {'user': user, 'text': text}, broadcast=True)

# Запуск
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=10000)
