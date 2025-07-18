from flask import Flask, redirect

app = Flask(__name__)

@app.route('/')
def index():
    return redirect('https://example.com')  # сюда подставь нужный адрес

if __name__ == '__main__':
    app.run()
