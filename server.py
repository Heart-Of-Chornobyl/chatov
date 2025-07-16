from flask import Flask, request, jsonify, session, send_from_directory, redirect, url_for
from flask_socketio import SocketIO, send, emit
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import random
import string
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret!'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins="*", engineio_logger=True)

# Папка со статикой
@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Инициализация базы
@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return "Сервер работает!"

@app.route('/generate_captcha', methods=['GET'])
def generate_captcha():
    captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    session['captcha'] = captcha
    return jsonify({'captcha': captcha})

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    captcha_input = data.get('captcha')

    if captcha_input != session.get('captcha'):
        return jsonify({"message": "Неверная капча!"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Пользователь уже существует!"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(username=username, password=hashed_password)
    db.session.add(user)
    db.session.commit()

    session['username'] = username
    return jsonify({"message": "Регистрация успешна!", "redirect": "/chat.html"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and bcrypt.check_password_hash(user.password, password):
        session['username'] = username
        return jsonify({"message": "Вход успешен!", "redirect": "/chat.html"}), 200
    else:
        return jsonify({"message": "Неверные данные!"}), 401

# Словарь для хранения приватных чатов по пользователю
private_chats = {}

# WebSocket обработка
@socketio.on('connect')
def handle_connect():
    username = session.get('username')
    if username:
        emit('message', f"{username} подключился к чату", broadcast=True)

@socketio.on('message')
def handle_message(msg):
    username = session.get('username', 'Аноним')
    if msg.startswith("@") and "," in msg:
        target, text = msg[1:].split(",", 1)
        emit('private_message', {"from": username, "to": target, "text": text}, broadcast=True)
    else:
        send(f"{username}: {msg}", broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)

