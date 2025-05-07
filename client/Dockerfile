FROM python:3.8-slim

WORKDIR /app

# Установка необходимых пакетов
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода и шаблонов
COPY client_service.py .
COPY templates/ templates/

# Установка curl для проверки здоровья
RUN apt-get update && apt-get install -y curl && apt-get clean

EXPOSE 5001

CMD ["python", "client_service.py"]