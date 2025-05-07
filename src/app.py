from flask import Flask, render_template, jsonify
import threading
import time
import random
import queue
import socket
import logging

app = Flask(__name__)

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Параметры задачи
v = 2  # Вариант (можно изменить)
s = 3  # Подгруппа (можно изменить)

# Рассчитываем количество парикмахеров и стульев
if v <= 5:
    k = (v + 3 + s)  # Количество парикмахеров
    n = 2 * v + 5 + 2 * s  # Количество стульев для ожидания
else:
    k = v - 3 + s  # Количество парикмахеров
    n = 2 * v - 6 + s  # Количество стульев для ожидания

# Глобальные переменные для отслеживания состояния
barbers = []  # Список парикмахеров
waiting_room = queue.Queue(maxsize=n)  # Очередь клиентов
customers_served = 0  # Счетчик обслуженных клиентов
customers_lost = 0  # Счетчик ушедших клиентов
simulation_running = False  # Флаг работы симуляции
simulation_lock = threading.Lock()  # Блокировка для обновления состояния
barber_locks = [threading.Lock() for _ in range(k)]  # Блокировки для каждого парикмахера
customer_threads = []  # Список потоков клиентов


class Barber:
    def __init__(self, id):
        self.id = id
        self.status = "sleeping"  # sleeping, cutting
        self.customer = None
        self.event = threading.Event()

    def sleep(self):
        self.status = "sleeping"
        logger.info(f"Парикмахер {self.id} спит")

    def wake_up(self, customer):
        self.status = "cutting"
        self.customer = customer
        self.event.set()
        logger.info(f"Парикмахер {self.id} проснулся и начал стричь клиента {customer.id}")

    def finish_haircut(self):
        customer_id = self.customer.id
        self.customer = None
        self.event.clear()
        logger.info(f"Парикмахер {self.id} закончил стрижку клиента {customer_id}")
        return customer_id


class Customer:
    def __init__(self, id):
        self.id = id
        self.status = "waiting"  # waiting, getting_haircut, done, left

    def set_status(self, status):
        self.status = status


def barber_work(barber_id):
    global customers_served
    barber = barbers[barber_id]

    while simulation_running:
        if waiting_room.empty() and barber.status != "cutting":
            with barber_locks[barber_id]:
                barber.sleep()
            barber.event.wait(1)  # Ждем клиента
            continue

        if barber.status == "sleeping" and not waiting_room.empty():
            try:
                customer = waiting_room.get_nowait()
                with barber_locks[barber_id]:
                    barber.wake_up(customer)
                customer.set_status("getting_haircut")

                # Имитация стрижки
                haircut_time = random.uniform(1, 5)  # Время стрижки 1-5 секунд
                time.sleep(haircut_time)

                # Завершение стрижки
                with barber_locks[barber_id]:
                    finished_customer_id = barber.finish_haircut()
                customer.set_status("done")

                # Обновляем количество обслуженных клиентов
                with simulation_lock:
                    customers_served += 1

                logger.info(f"Клиент {finished_customer_id} пострижен и уходит")
            except queue.Empty:
                pass  # Кто-то другой взял клиента
        time.sleep(0.1)  # Небольшая задержка



def generate_customers():
    global customers_lost
    customer_id = 0

    while simulation_running:
        # Генерируем нового клиента с некоторой задержкой
        time.sleep(random.uniform(0.5, 3))

        if not simulation_running:
            break

        customer = Customer(customer_id)
        customer_id += 1

        # Пытаемся добавить клиента в очередь ожидания
        try:
            waiting_room.put_nowait(customer)
            logger.info(f"Клиент {customer.id} зашел в парикмахерскую и ждет")

            # Проверяем, есть ли спящие парикмахеры
            for barber_id, barber in enumerate(barbers):
                if barber.status == "sleeping":
                    barber.event.set()  # Будим одного парикмахера
                    break
        except queue.Full:
            customer.set_status("left")
            with simulation_lock:
                customers_lost += 1
            logger.info(f"Клиент {customer.id} не нашел свободных мест и ушел")


def initialize_simulation():
    global barbers, customers_served, customers_lost, simulation_running, customer_threads

    # Сбрасываем состояние
    barbers = [Barber(i) for i in range(k)]
    customers_served = 0
    customers_lost = 0

    # Очищаем очередь ожидания
    while not waiting_room.empty():
        try:
            waiting_room.get_nowait()
        except queue.Empty:
            break

    # Запускаем потоки парикмахеров
    simulation_running = True
    barber_threads = [threading.Thread(target=barber_work, args=(i,), daemon=True) for i in range(k)]
    for thread in barber_threads:
        thread.start()

    # Запускаем поток генерации клиентов
    customer_generator = threading.Thread(target=generate_customers, daemon=True)
    customer_generator.start()

    customer_threads = barber_threads + [customer_generator]


def stop_simulation():
    global simulation_running
    simulation_running = False
    # Ждем немного, чтобы потоки завершились
    time.sleep(1)


@app.route('/')
def home():
    hostname = socket.gethostname()
    return render_template('index.html',
                           hostname=hostname,
                           barbers_count=k,
                           waiting_seats=n,
                           variant=v,
                           subgroup=s)


@app.route('/start', methods=['POST'])
def start_simulation():
    initialize_simulation()
    return jsonify({'status': 'started'})


@app.route('/stop', methods=['POST'])
def stop_simulation_route():
    stop_simulation()
    return jsonify({'status': 'stopped'})


@app.route('/status')
def get_status():
    barbers_status = []

    for i, barber in enumerate(barbers):
        with barber_locks[i]:
            status = {
                'id': barber.id,
                'status': barber.status,
                'customer': barber.customer.id if barber.customer else None
            }
            barbers_status.append(status)

    waiting_customers = waiting_room.qsize()

    return jsonify({
        'barbers': barbers_status,
        'waiting_customers': waiting_customers,
        'customers_served': customers_served,
        'customers_lost': customers_lost,
        'is_running': simulation_running
    })


@app.route('/health')
def health():
    return jsonify({"status": "healthy"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
