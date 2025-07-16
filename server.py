import gevent.monkey
gevent.monkey.patch_all()

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import random
import string

# Настройки приложения
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # SQLite база данных
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret!'  # Используем секретный ключ

# Инициализация базы данных и bcrypt
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Инициализация базы данных
@app.before_request
def create_tables():
    with app.app_context():
        db.create_all()  # Создаём таблицы в контексте приложения

# Эндпоинт для генерации капчи
@app.route('/generate_captcha', methods=['GET'])
def generate_captcha():
    captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))  # Генерация капчи
    return jsonify({'captcha': captcha})

# Маршрут главной страницы
@app.route('/')
def index():
    return "Сервер работает!"

# Маршрут регистрации
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()  # Получаем данные как JSON

    username = data.get('username')
    password = data.get('password')
    captcha_input = data.get('captcha')

    # Генерация капчи для проверки
    captcha_answer = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    if captcha_input != captcha_answer:
        return jsonify({"message": "Неверная капча!"}), 400

    # Проверяем, существует ли уже пользователь
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Пользователь с таким именем уже существует!"}), 400

    # Хешируем пароль
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Добавляем нового пользователя в базу данных
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Регистрация успешна!"}), 201

# Маршрут для входа
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()  # Получаем данные как JSON
    username = data.get('username')
    password = data.get('password')

    # Находим пользователя в базе данных
    user = User.query.filter_by(username=username).first()

    # Проверка пароля
    if user and bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Вход успешен!"}), 200
    else:
        return jsonify({"message": "Неверные данные для входа!"}), 401

if __name__ == '__main__':
    app.run(debug=True)
