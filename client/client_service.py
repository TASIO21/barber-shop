from flask import Flask, render_template, redirect, url_for
import requests
import socket
import os

app = Flask(__name__)

# Получаем адрес сервера парикмахеров из переменной среды или используем значение по умолчанию
BARBER_SERVICE_HOST = os.environ.get('BARBER_SERVICE_HOST', 'barber-service')
BARBER_SERVICE_PORT = os.environ.get('BARBER_SERVICE_PORT', '5000')
BARBER_SERVICE_URL = f"http://{BARBER_SERVICE_HOST}:{BARBER_SERVICE_PORT}"


@app.route('/')
def home():
    # Получаем текущий hostname для отображения
    hostname = socket.gethostname()

    try:
        # Получаем статус от сервиса парикмахеров
        status_response = requests.get(f"{BARBER_SERVICE_URL}/status")
        status_data = status_response.json()

        return render_template('index.html',
                               hostname=hostname,
                               barbers_count=status_data['barbers_count'],
                               waiting_seats=status_data['waiting_seats'],
                               variant=status_data['variant'],
                               subgroup=status_data['subgroup'],
                               is_running=status_data['is_running'],
                               barbers=status_data['barbers'],
                               waiting_customers=status_data['waiting_customers'],
                               customers_served=status_data['customers_served'],
                               customers_lost=status_data['customers_lost'])
    except Exception as e:
        # В случае ошибки показываем страницу с сообщением об ошибке
        return render_template('error.html', error=str(e), service_url=BARBER_SERVICE_URL)


@app.route('/start', methods=['POST'])
def start_simulation():
    try:
        response = requests.post(f"{BARBER_SERVICE_URL}/start")
        return redirect(url_for('home'))
    except Exception as e:
        return render_template('error.html', error=str(e), service_url=BARBER_SERVICE_URL)


@app.route('/stop', methods=['POST'])
def stop_simulation():
    try:
        response = requests.post(f"{BARBER_SERVICE_URL}/stop")
        return redirect(url_for('home'))
    except Exception as e:
        return render_template('error.html', error=str(e), service_url=BARBER_SERVICE_URL)


@app.route('/health')
def health():
    try:
        # Проверяем также здоровье сервиса парикмахеров
        barber_health = requests.get(f"{BARBER_SERVICE_URL}/health").json()
        return {"status": "healthy", "barber_service": barber_health["status"]}
    except:
        return {"status": "healthy", "barber_service": "unreachable"}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)