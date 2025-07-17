from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from flask_session import Session

app = Flask(__name__)
CORS(app)

# Конфигурация базы данных PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://chat_db_6jqp_user:N89VOuIv1nDWhsSE6mTuIFYNarI4LyVx@dpg-d1s4c8ngi27c73dm04t0-a.oregon-postgres.render.com/chat_db_6jqp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Секретный ключ для сессий
app.config['SECRET_KEY'] = 'секрет_для_сессий_замени_на_свой'

# Настройка сессий через сервер (можно использовать filesystem или другую)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

db = SQLAlchemy(app)

# Модель пользователя
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Модель сообщения в чате
class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', backref=db.backref('messages', lazy=True))

# Создание таблиц при старте (один раз)
@app.before_first_request
def create_tables():
    db.create_all()

# Регистрация нового пользователя
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'User already exists'}), 400

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'})

# Вход пользователя
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({'message': 'Login successful'})
    else:
        return jsonify({'error': 'Invalid username or password'}), 401

# Выход пользователя
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

# Добавление сообщения в чат
@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    content = data.get('content')
    if not content:
        return jsonify({'error': 'Message content required'}), 400

    message = Message(user_id=session['user_id'], content=content)
    db.session.add(message)
    db.session.commit()

    return jsonify({'message': 'Message sent'})

# Получение последних 50 сообщений
@app.route('/messages', methods=['GET'])
def get_messages():
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
    messages.reverse()  # чтобы были в порядке отправки

    result = []
    for msg in messages:
        result.append({
            'id': msg.id,
            'username': msg.user.username,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        })
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
