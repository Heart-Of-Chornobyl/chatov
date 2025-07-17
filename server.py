import os
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_session import Session
from flask_cors import CORS
from flask_socketio import SocketIO
from gevent import monkey
monkey.patch_all()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecretkey')

# Подключение к БД через переменную окружения
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("WARNING: DATABASE_URL not set, using local SQLite database.")
    DATABASE_URL = 'sqlite:///chat.db'

# Для Render нужно, чтобы URL был в формате postgresql+psycopg2:// и sslmode=require
if DATABASE_URL.startswith('postgresql://') and '+psycopg2' not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://')

if 'sslmode' not in DATABASE_URL:
    # Добавляем sslmode=require если не указан (важно для Render)
    if '?' in DATABASE_URL:
        DATABASE_URL += '&sslmode=require'
    else:
        DATABASE_URL += '?sslmode=require'

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Сессии
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# CORS
CORS(app)

# Инициализация
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# Модели
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)

try:
    db.create_all()
    print("Database tables created or verified.")
except Exception as e:
    print("Error during database initialization:", e)

# Роуты (пример)
@app.route('/')
def index():
    if 'user_id' in session:
        return f"Hello, user {session['user_id']}!"
    else:
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect('/')
        else:
            return "Invalid username or password", 401
    return render_template('login.html')

@app.route('/reg', methods=['GET', 'POST'])
def reg_page():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return "User already exists", 400
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template('reg.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
