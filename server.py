import os
from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

app = Flask(__name__, template_folder=os.path.dirname(os.path.abspath(__file__)))
app.config['SECRET_KEY'] = 'your_secret_key_here'

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://chat_db_6jqp_user:N89VOuIv1nDWhsSE6mTuIFYNarI4LyVx@dpg-d1s4c8ngi27c73dm04t0-a.oregon-postgres.render.com/chat_db_6jqp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    username = db.Column(db.String(80))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return render_template('reg.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    # Используем ORM, а не raw execute!
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'User already exists'}), 400

    new_user = User(
        username=username,
        password_hash=generate_password_hash(password)
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'success': 'User registered'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({'success': 'Logged in'})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html', username=session['username'])

@socketio.on('send_message')
def handle_send_message(data):
    if 'user_id' not in session:
        return
    msg = Message(user_id=session['user_id'], username=session['username'], content=data['message'])
    db.session.add(msg)
    db.session.commit()
    emit('receive_message', {
        'username': session['username'],
        'message': data['message'],
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    }, broadcast=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
