FROM python:3.11-slim

# Не буферизовать вывод, удобно для логов
ENV PYTHONUNBUFFERED=1

# Рабочая директория
WORKDIR /app

# Устанавливаем системные зависимости (для psycopg2 и т.п.)
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Копируем requirements и ставим зависимости
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё приложение
COPY . .

# Порт для uvicorn
EXPOSE 8000

# Команда по умолчанию:
# 1) прогнать миграции Alembic
# 2) запустить uvicorn
CMD alembic upgrade head && \
<<<<<<< HEAD
    uvicorn main:app --host 0.0.0.0 --port 8000
=======
    uvicorn main:app --host 0.0.0.0 --port 8000
>>>>>>> 4077ef73a642438935e6af76ec086a5aa7436986
