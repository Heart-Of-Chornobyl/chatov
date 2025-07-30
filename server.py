from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import mysql.connector
import requests
import bcrypt

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': '31.128.174.187',
    'port': 3306,
    'user': 'darkchat',
    'password': 'StrongPass123!',
    'database': 'darkchat',
    'connect_timeout': 5
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Помилка підключення до БД: {err}")
        return None

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def verify_recaptcha(token):
    secret_key = os.environ.get('RECAPTCHA_SECRET_KEY')
    if not secret_key:
        return False
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
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'message': 'Заповніть всі поля'}), 400

    if email == '':
        email = None

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Помилка підключення до бази'}), 500

    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                  (username, email, hash_password(password)))
        conn.commit()
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Користувач з таким логіном або email вже існує'}), 409
    finally:
        c.close()
        conn.close()

    return jsonify({'success': True, 'message': 'Реєстрація успішна'}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    token = data.get('recaptcha_token')
    if not token or not verify_recaptcha(token):
        return jsonify({'success': False, 'message': 'Капча не пройдена'}), 400

    username_or_email = data.get('username', '').strip()
    password = data.get('password', '').strip()

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Помилка підключення до бази'}), 500

    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = %s OR email = %s',
              (username_or_email, username_or_email))
    user = c.fetchone()
    c.close()
    conn.close()

    if user and check_password(password, user[0]):
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
