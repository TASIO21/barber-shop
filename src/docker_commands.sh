# Создание Docker образа
docker build -t my-app .

# Запуск контейнера
docker run -d -p 5000:5000 my-app

# Проверка запущенных контейнеров
docker ps

# Остановка контейнера (замените CONTAINER_ID на фактический ID контейнера)
docker stop fd2d1a595fd8