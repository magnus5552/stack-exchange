from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Явно импортируем redis для проверки доступности
import redis

# Проверка подключения к Redis
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST, 
        port=settings.REDIS_PORT,
        socket_connect_timeout=5
    )
    redis_client.ping()
    print(f"Успешное подключение к Redis по адресу {settings.REDIS_HOST}:{settings.REDIS_PORT}")
except Exception as e:
    print(f"Ошибка подключения к Redis: {str(e)}")
    # Не выбрасываем исключение, продолжаем инициализацию

celery_app = Celery(
    "exchange_tasks",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
)

celery_app.conf.task_routes = {
    "app.tasks.balance_tasks.*": {"queue": "balance_queue"},
    "app.tasks.transaction_tasks.*": {"queue": "transaction_queue"},
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)
