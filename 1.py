from flask import Flask
import mysql.connector
from mysql.connector import Error
import os

app = Flask(__name__)

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.environ.get('DB_HOST'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASS'),
            database=os.environ.get('DB_NAME'),
            port=int(os.environ.get('DB_PORT', 3306))  # порт за замовчуванням 3306
        )
        if connection.is_connected():
            print("Підключення до БД успішне")
            return connection
    except Error as e:
        print(f"Помилка підключення до БД: {e}")
        return None

@app.route('/test-db')
def test_db():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"Підключено до бази даних: {db_name[0]}"
    else:
        return "Не вдалося підключитися до бази даних"

if __name__ == "__main__":
    app.run(debug=True)
