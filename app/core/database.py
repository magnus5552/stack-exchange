from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
import logging
import time
import contextlib
from typing import Dict
import threading
from datetime import datetime

from app.core.config import settings

# Настройка расширенного логгера для пула соединений
logger = logging.getLogger("sqlalchemy.pool")

# Счетчик активных транзакций
active_transactions: Dict[int, datetime] = {}
transactions_lock = threading.Lock()

# Параметры пула соединений для высокой нагрузки (50+ RPS):
# - pool_size: увеличен до 100 соединений в пуле (рассчитан на 50+ RPS)
# - max_overflow: до 200 дополнительных соединений при пиковых нагрузках
# - pool_pre_ping: проверка соединений перед каждым использованием
# - pool_recycle: сокращен до 600 секунд для обновления соединений
# - pool_timeout: увеличен для предотвращения ошибок при высокой нагрузке
# - pool_use_lifo: использование LIFO для более эффективного использования кеша
engine = create_engine(
    settings.DB_CONN_STRING,
    echo=settings.DB_ECHO,
    poolclass=QueuePool,
    pool_size=100,  # Увеличен размер пула для 50+ RPS
    max_overflow=200,  # Больше резервных соединений для пиковых нагрузок
    pool_pre_ping=True,  # Проверка соединений перед использованием
    pool_recycle=600,  # Обновление соединений каждые 10 минут
    pool_timeout=60,  # Увеличено время ожидания свободного соединения
    pool_use_lifo=True,  # Стратегия LIFO для лучшего использования соединений
    connect_args={
        'connect_timeout': 10,  # Таймаут установки соединения
        'keepalives': 1,  # Поддержка TCP keepalive
        'keepalives_idle': 60,  # Время простоя до отправки keepalive (секунды)
        'keepalives_interval': 10,  # Интервал между keepalive пакетами (секунды)
        'keepalives_count': 5,  # Количество попыток keepalive
        'application_name': 'trading_app'  # Идентификация в логах БД
    },
    # Использование многопоточности для чтения результатов (при поддержке драйвером)
    # execution_options={'stream_results': True}
)

# Расширенный мониторинг пула соединений
@event.listens_for(engine, "checkout")
def checkout_handler(dbapi_conn, conn_record, conn_proxy):
    try:
        conn_id = id(dbapi_conn)
        conn_record.info.setdefault('checkout_time', time.time())
        with transactions_lock:
            active_transactions[conn_id] = datetime.now()
        
        # Проверка на количество используемых соединений
        total_used = len(active_transactions)
        pool_status = f"Занято: {total_used}, Всего: {engine.pool.size()}, Макс: {engine.pool.size() + engine.pool.overflow()}"
        
        # Предупреждение при приближении к лимиту
        threshold = engine.pool.size() * 0.8
        if total_used > threshold:
            logger.warning(f"Высокая загрузка пула соединений! {pool_status}")
        else:
            logger.debug(f"Соединение взято из пула. {pool_status}")
        
        # Мониторинг долгих транзакций
        @event.listens_for(engine, "checkin", once=True)
        def checkin_conn(dbapi_connection, connection_record):
            duration = time.time() - connection_record.info['checkout_time']
            if duration > 2.0:  # Предупреждение о долгих транзакциях
                logger.warning(f"Долгая транзакция: {duration:.2f} секунд")
    except Exception as e:
        logger.error(f"Ошибка мониторинга соединения: {e}")

@event.listens_for(engine, "checkin")
def checkin_handler(dbapi_conn, conn_record):
    try:
        conn_id = id(dbapi_conn)
        with transactions_lock:
            if conn_id in active_transactions:
                checkout_time = active_transactions.pop(conn_id)
                duration = (datetime.now() - checkout_time).total_seconds()
                if duration > 0.5:  # Логирование при долгих транзакциях
                    logger.info(f"Транзакция завершена за {duration:.2f} сек (соединение {conn_id})")
        
        logger.debug(f"Соединение возвращено в пул. Активных: {len(active_transactions)}")
    except Exception as e:
        logger.error(f"Ошибка при возврате соединения: {e}")

# Фабрика сессий с оптимизированными настройками
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False  # Ускорение за счет отказа от инвалидации объектов
    )
)

# Контекстный менеджер для отслеживания времени выполнения запросов
@contextlib.contextmanager
def timed_session():
    start = time.time()
    session = SessionLocal()
    try:
        yield session
        duration = time.time() - start
        if duration > 0.1:  # Логируем только медленные запросы
            logger.info(f"Завершена транзакция БД за {duration:.3f} сек")
    except (DBAPIError, SQLAlchemyError) as e:
        logger.error(f"Ошибка БД ({time.time() - start:.3f} сек): {str(e)}")
        raise
    finally:
        session.close()

def get_db():
    """
    Оптимизированная функция предоставления сессии БД с автоматическим управлением соединениями.
    Использует привязку к текущему потоку/запросу и закрывает сессию после использования.
    
    Имеет встроенную обработку исключений и мониторинг производительности.
    """
    start_time = time.time()
    db = SessionLocal()
    try:
        yield db
    except DBAPIError as e:
        # Логирование ошибок базы данных
        logger.error(f"Ошибка БД: {str(e)}. Время: {time.time() - start_time:.3f} сек")
        raise
    finally:
        # Оптимизация: закрываем сессию, возвращая соединение в пул
        db.close()
        # Логирование долгих транзакций
        duration = time.time() - start_time
        if duration > 0.5:  # Порог для "медленных" транзакций
            logger.warning(f"Долгая транзакция: {duration:.3f} сек")
