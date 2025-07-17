from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'твой_секретный_ключ_сюда'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://chat_db_lwq3_user:qKaqAEbbnUB5VQ7olYRvQmQRSmAGWyqi@dpg-d1s7il0dl3ps739uq8p0-a.oregon-postgres.render.com/chat_db_lwq3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)  # Если фронтенд отдельно, для разрешения CORS

# --- Модели ---

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('messages', lazy=True))


# --- Создание таблиц ---
@app.before_first_request
def create_tables():
    db.create_all()


# --- Роуты ---

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


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401

    session['user_id'] = user.id
    session['username'] = user.username
    return jsonify({'message': 'Logged in successfully'})


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'})


@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    content = data.get('content')
    if not content:
        return jsonify({'error': 'Message content required'}), 400

    msg = Message(user_id=session['user_id'], content=content)
    db.session.add(msg)
    db.session.commit()

    return jsonify({'message': 'Message sent'})


@app.route('/get_messages', methods=['GET'])
def get_messages():
    # Вернем последние 50 сообщений с именами пользователей и временем
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
    messages.reverse()  # чтобы показать в хронологическом порядке

    result = []
    for m in messages:
        result.append({
            'id': m.id,
            'username': m.user.username,
            'content': m.content,
            'timestamp': m.timestamp.isoformat()
        })
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
