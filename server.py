from flask import Flask, request, jsonify, send_from_directory, session, g
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import random
import string
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_url_path='', static_folder='.')
app.secret_key = 'секретный_ключ'
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

DATABASE = 'chat.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            text TEXT NOT NULL
        )
    ''')
    db.commit()

@app.route('/generate_captcha')
def generate_captcha():
    captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    session['captcha'] = captcha
    return jsonify({'captcha': captcha})

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    captcha = data.get('captcha', '').strip()
    if not username or not password or not captcha:
        return jsonify({'message': 'Заполните все поля'}), 400
    if captcha != session.get('captcha'):
        return jsonify({'message': 'Неверная капча'}), 400

    db = get_db()
    cursor = db.execute('SELECT id FROM users WHERE username = ?', (username,))
    if cursor.fetchone() is not None:
        return jsonify({'message': 'Пользователь уже существует'}), 400

    hashed_password = generate_password_hash(password)
    db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    db.commit()
    session['username'] = username
    return jsonify({'message': 'Регистрация успешна'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    db = get_db()
    cursor = db.execute('SELECT password FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    if row is None or not check_password_hash(row['password'], password):
        return jsonify({'message': 'Неверные данные'}), 400

    session['username'] = username
    return jsonify({'message': 'Вход выполнен'})

@app.route('/')
def root():
    return send_from_directory('.', 'reg.html')

@app.route('/chat.html')
def chat_page():
    return send_from_directory('.', 'chat.html')

@socketio.on('connect')
def handle_connect():
    if 'username' not in session:
        return False
    db = get_db()
    cursor = db.execute('SELECT username, text FROM messages ORDER BY id')
    messages = [{'user': row['username'], 'text': row['text']} for row in cursor.fetchall()]
    emit('load_messages', messages)

@socketio.on('send_message')
def handle_send(data):
    username = session.get('username', 'Аноним')
    text = data.get('text', '').strip()
    if not text:
        return

    db = get_db()
    db.execute('INSERT INTO messages (username, text) VALUES (?, ?)', (username, text))
    db.commit()

    cursor = db.execute('SELECT COUNT(*) FROM messages')
    count = cursor.fetchone()[0]
    if count > 100:
        to_delete = count - 100
        db.execute('DELETE FROM messages WHERE id IN (SELECT id FROM messages ORDER BY id LIMIT ?)', (to_delete,))
        db.commit()

    message = {'user': username, 'text': text}
    emit('new_message', message, broadcast=True)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    socketio.run(app, host='0.0.0.0', port=10000)
