import os
import random
import string
from flask import Flask, request, jsonify, session, redirect, render_template
from flask_cors import CORS
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# Строка подключения к PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://chat_db_lwq3_user:qKaqAEbbnUB5VQ7olYRvQmQRSmAGWyqi@dpg-d1s7il0dl3ps739uq8p0-a.oregon-postgres.render.com/chat_db_lwq3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Настройка сессий
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_PERMANENT'] = False

# Инициализация
CORS(app, supports_credentials=True)
db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db
Session(app)
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False)

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

# Капча
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
        return jsonify({'message': 'Все поля обязательны'}), 400

    if captcha.upper() != session.get('captcha', '').upper():
        return jsonify({'message': 'Неверная капча'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Пользователь уже существует'}), 400

    hashed_pw = generate_password_hash(password)
    db.session.add(User(username=username, password_hash=hashed_pw))
    db.session.commit()
    session['username'] = username
    return jsonify({'message': 'Регистрация успешна'})

# Вход
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Неверное имя пользователя или пароль'}), 400

    session['username'] = username
    return jsonify({'message': 'Вход успешен'})

# Выход
@app.route('/logout')
def logout():
    session.pop('username', None)
    return jsonify({'message': 'Выход выполнен'})

# Страницы
@app.route('/')
def index():
    return redirect('/reg')

@app.route('/reg')
def reg_page():
    return render_template('reg.html')

@app.route('/chat')
def chat_page():
    if 'username' not in session:
        return redirect('/reg')
    return render_template('chat.html')

# Сокеты
@socketio.on('connect')
def handle_connect():
    if 'username' not in session:
        return False
    msgs = Message.query.order_by(Message.id.asc()).all()
    emit('load_messages', [{'user': m.user, 'text': m.text} for m in msgs])

@socketio.on('send_message')
def handle_send_message(data):
    if 'username' not in session:
        return
    text = data.get('text', '').strip()
    if not text:
        return
    msg = Message(user=session['username'], text=text)
    db.session.add(msg)
    db.session.commit()
    emit('new_message', {'user': msg.user, 'text': msg.text}, broadcast=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=10000)

# --- Запуск и создание таблиц ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # создаём таблицы, если ещё нет
    socketio.run(app, host='0.0.0.0', port=10000)
