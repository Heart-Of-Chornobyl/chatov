from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sqlite3
import hashlib
import requests  # для перевірки reCAPTCHA

app = Flask(__name__)
CORS(app)

DB_FILE = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_recaptcha(token):
    secret_key = "6LejYZQrAAAAAK6HU9hHqHFsPWOFDEoLn1_nYqxW"  # встав сюди свій секретний ключ reCAPTCHA
    payload = {
        'secret': secret_key,
        'response': token
    }
    r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
    result = r.json()
    return result.get('success', False)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    token = data.get('recaptcha_token')
    if not token or not verify_recaptcha(token):
        return jsonify({'success': False, 'message': 'Капча не пройдена'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'message': 'Заповніть всі поля'}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                  (username, hash_password(password)))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Користувач вже існує'}), 409
    finally:
        conn.close()

    return jsonify({'success': True, 'message': 'Реєстрація успішна'}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    token = data.get('recaptcha_token')
    if not token or not verify_recaptcha(token):
        return jsonify({'success': False, 'message': 'Капча не пройдена'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()

    if user and user[0] == hash_password(password):
        return jsonify({'success': True, 'message': 'Успішний вхід'}), 200
    else:
        return jsonify({'success': False, 'message': 'Невірний логін або пароль'}), 401

@app.route('/')
def auth_page():
    return send_from_directory('.', 'auth.html')

@app.route('/<page>')
def static_page(page):
    if os.path.exists(page):
        return send_from_directory('.', page)
    return '404 Not Found', 404

@app.route('/pages/<page>')
def pages_dir(page):
    return send_from_directory('pages', page)

@app.route('/js/<file>')
def js_dir(file):
    return send_from_directory('js', file)

@app.route('/styles/<file>')
def css_dir(file):
    return send_from_directory('styles', file)

@app.route('/js/emoji.json')
def emoji_json():
    return send_from_directory('js', 'emoji.json')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
