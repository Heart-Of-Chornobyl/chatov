import os
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_session import Session
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from supabase import create_client

# Инициализация Flask приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecretkey')

# Настройка Supabase
SUPABASE_URL = 'https://lbppkscrjvjzcjalwkg.supabase.co'  # Замените на свой URL
SUPABASE_KEY = 'your-supabase-api-key'  # Замените на свой API ключ
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Настройка SQLAlchemy для Supabase
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://postgres:{SUPABASE_KEY}@{SUPABASE_URL}/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'

Session(app)
CORS(app, supports_credentials=True)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# Хранение пользователей, которые сейчас онлайн
online_users = set()

# Модели данных для пользователей и сообщений
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_url = db.Column(db.String(255), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(50), nullable=True)

# Инициализация базы данных
try:
    with app.app_context():
        db.create_all()
    print("✅ Database tables created or verified.")
except Exception as e:
    print("❌ Error during database initialization:", e)

# Роуты для регистрации и входа
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/chat.html')
    return redirect('/login')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return jsonify({'message': 'Login successful'}), 200
        return jsonify({'message': 'Invalid credentials'}), 401
    return render_template('reg.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already taken'}), 409

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    return jsonify({'message': 'Registration successful'}), 200

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# Роут для чата
@app.route('/chat.html')
def chat_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('chat.html')

# 💬 Socket.IO

@socketio.on('connect')
def handle_connect():
    user_id = session.get('user_id')
    if not user_id:
        return False  # Отклонить подключение

    user = User.query.get(user_id)
    if not user:
        return False

    # Добавляем пользователя в онлайн множество
    online_users.add(user.username)
    # Рассылаем всем обновление статусов
    socketio.emit('user_statuses', {u: 'online' for u in online_users})

    messages = Message.query.order_by(Message.id.asc()).all()
    emit('load_messages', [{'user': User.query.get(m.user_id).username, 'text': m.content, 'file_url': m.file_url, 'file_name': m.file_name, 'file_type': m.file_type} for m in messages])

@socketio.on('disconnect')
def handle_disconnect():
    user_id = session.get('user_id')
    if not user_id:
        return
    user = User.query.get(user_id)
    if not user:
        return

    online_users.discard(user.username)
    socketio.emit('user_statuses', {u: 'online' for u in online_users})

@socketio.on('send_message')
def handle_send_message(data):
    user_id = session.get('user_id')
    if not user_id:
        return

    user = User.query.get(user_id)
    if not user:
        return

    text = data.get('text', '').strip()
    if not text:
        return

    total_messages = Message.query.count()
    if total_messages >= 50:
        oldest = Message.query.order_by(Message.id.asc()).first()
        if oldest:
            db.session.delete(oldest)
            db.session.commit()

    msg = Message(user_id=user.id, content=text)
    db.session.add(msg)
    db.session.commit()

    emit('new_message', {'user': user.username, 'text': text}, broadcast=True)

@socketio.on('send_file')
def handle_send_file(data):
    user_id = session.get('user_id')
    if not user_id:
        return

    user = User.query.get(user_id)
    if not user:
        return

    filename = data.get('filename')
    filedata = data.get('filedata')  # base64-строка с префиксом "data:..."

    if not filename or not filedata:
        return

    # Загружаем файл в Supabase Storage
    bucket = supabase.storage.from_('bucket')
    path = f"chat/{filename}"
    result = bucket.upload(path, filedata)

    # Получаем публичный URL для скачивания
    public_url = bucket.get_public_url(path).data['publicUrl']

    emit('new_file', {
        'user': user.username,
        'filename': filename,
        'filedata': public_url
    }, broadcast=True)

# ▶️ Запуск
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
