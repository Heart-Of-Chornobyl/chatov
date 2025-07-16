from flask import Flask, render_template
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return "Сервер чата работает!"

@socketio.on('message')
def handle_message(msg):
    print(f"Получено сообщение: {msg}")
    send(msg, broadcast=True)  # Отправляем всем подключённым
    
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, allow_unsafe_werkzeug=True)
