from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'твой_секретный_ключ_здесь'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://chat_db_6jqp_user:N89VOuIv1nDWhsSE6mTuIFYNarI4LyVx@dpg-d1s4c8ngi27c73dm04t0-a.oregon-postgres.render.com/chat_db_6jqp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app, supports_credentials=True)

# --- Модели ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, nullable=False)

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
    captcha_input = data.get('captcha', '').strip().upper()

    if not username or not password or not captcha_input:
        return jsonify({'message': 'Заполните все поля'}), 400

    if session.get('captcha') != captcha_input:
        return jsonify({'message': 'Неверная капча'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Пользователь с таким именем уже существует'}), 400

    password_hash = generate_password_hash(password)
    new_user = User(username=username, password_hash=password_hash)
    db.session.add(new_user)
    db.session.commit()

    session.pop('captcha', None)
    session['username'] = username
    return jsonify({'message': 'Регистрация успешна'}), 200

# --- Вход ---

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'message': 'Заполните все поля'}), 400

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Неверное имя пользователя или пароль'}), 400

    session['username'] = username
    return jsonify({'message': 'Вход успешен'}), 200

# --- Чат Socket.IO ---

@socketio.on('connect')
def handle_connect():
    # При подключении отправляем все сообщения
    messages = Message.query.order_by(Message.id).all()
    msgs = [{'user': m.username, 'text': m.text} for m in messages]
    emit('load_messages', msgs)

@socketio.on('send_message')
def handle_send_message(data):
    username = session.get('username')
    if not username:
        emit('new_message', {'user': 'System', 'text': 'Ошибка: пользователь не авторизован'})
        return

    text = data.get('text', '').strip()
    if not text:
        return

    msg = Message(username=username, text=text)
    db.session.add(msg)
    db.session.commit()

    emit('new_message', {'user': username, 'text': text}, broadcast=True)

# --- Запуск и создание таблиц ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=10000)
