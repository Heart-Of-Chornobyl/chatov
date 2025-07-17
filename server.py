import os
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_session import Session
from flask_cors import CORS
from flask_socketio import SocketIO
from gevent import monkey

monkey.patch_all()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecretkey')

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("WARNING: DATABASE_URL not set, using local SQLite database.")
    DATABASE_URL = 'sqlite:///chat.db'

if DATABASE_URL.startswith('postgresql://') and '+psycopg2' not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://')

if 'sslmode' not in DATABASE_URL:
    if '?' in DATABASE_URL:
        DATABASE_URL += '&sslmode=require'
    else:
        DATABASE_URL += '?sslmode=require'

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
CORS(app)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

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

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/chat')
    else:
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
@app.route('/reg', methods=['GET', 'POST'])
def login_reg():
    error = None
    if request.method == 'POST':
        action = request.form.get('action')  # 'login' или 'register'
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            error = "Введите логин и пароль"
        else:
            if action == 'login':
                user = User.query.filter_by(username=username).first()
                if user and user.check_password(password):
                    session['user_id'] = user.id
                    return redirect('/chat')
                else:
                    error = "Неверный логин или пароль"
            elif action == 'register':
                if User.query.filter_by(username=username).first():
                    error = "Пользователь уже существует"
                else:
                    new_user = User(username=username)
                    new_user.set_password(password)
                    db.session.add(new_user)
                    db.session.commit()
                    session['user_id'] = new_user.id
                    return redirect('/chat')
            else:
                error = "Неизвестное действие"

    return render_template('reg.html', error=error)

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('chat.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
