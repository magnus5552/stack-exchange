FROM python:3.10-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка необходимых зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY app/ ./app/

# Указываем порт
EXPOSE 8000

# Настройка ожидания запуска PostgreSQL
COPY wait-for-postgres.sh /wait-for-postgres.sh
RUN chmod +x /wait-for-postgres.sh

# Запуск приложения
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info