import os
from flask import Flask, request, session, redirect, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get("SECRET_KEY", "devkey")

# Настройки базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
db = SQLAlchemy(app)
socketio = SocketIO(app, manage_session=False)

# Модели
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(32), nullable=False)
    text = db.Column(db.Text, nullable=False)

# Создание таблиц
with app.app_context():
    db.create_all()

@app.route('/')
def root():
    return redirect('/static/reg.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': 'Пользователь уже существует'})

    hashed = generate_password_hash(password)
    db.session.add(User(username=username, password_hash=hashed))
    db.session.commit()
    session['username'] = username
    return jsonify({'success': True})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        session['username'] = username
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Неверный логин или пароль'})

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect('/')
    return send_from_directory('static', 'chat.html')

# WebSocket
@socketio.on('connect')
def on_connect():
    if 'username' not in session:
        return False  # Отключить сокет
    msgs = Message.query.order_by(Message.id).all()
    emit('load_messages', [{'user': m.user, 'text': m.text} for m in msgs])

@socketio.on('send_message')
def handle_send(data):
    if 'username' not in session:
        return
    msg = Message(user=session['username'], text=data['text'])
    db.session.add(msg)
    db.session.commit()
    emit('new_message', {'user': msg.user, 'text': msg.text}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
