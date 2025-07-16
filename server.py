import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, send
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
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
socketio = SocketIO(app, cors_allowed_origins="*")

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Инициализация базы данных
@app.before_first_request
def create_tables():
    db.create_all()

# Форма для регистрации с капчей
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    captcha = StringField('Enter the text: ' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)), 
                          validators=[DataRequired()])
    submit = SubmitField('Register')

@app.route('/')
def index():
    return "Сервер работает!"

# Маршрут регистрации
@app.route('/register', methods=['POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        captcha_input = form.captcha.data

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
    return jsonify({"message": "Ошибка в данных формы!"}), 400

# Маршрут для входа
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Находим пользователя в базе данных
    user = User.query.filter_by(username=username).first()

    # Проверка пароля
    if user and bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Вход успешен!"}), 200
    else:
        return jsonify({"message": "Неверные данные для входа!"}), 401

# WebSocket для чата
@socketio.on('message')
def handle_message(msg):
    send(msg, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)
