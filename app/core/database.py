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

logger = logging.getLogger("sqlalchemy.pool")

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
    pool_size=100,
    max_overflow=200,
    pool_pre_ping=True,
    pool_recycle=600,
    pool_timeout=60,
    pool_use_lifo=True,
    connect_args={
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 60,
        'keepalives_interval': 10,
        'keepalives_count': 5,
        'application_name': 'trading_app'
    },
    # Использование многопоточности для чтения результатов (при поддержке драйвером)
    # execution_options={'stream_results': True}
)

@event.listens_for(engine, "checkout")
def checkout_handler(dbapi_conn, conn_record, conn_proxy):
    try:
        conn_id = id(dbapi_conn)
        conn_record.info.setdefault('checkout_time', time.time())
        with transactions_lock:
            active_transactions[conn_id] = datetime.now()
        
        total_used = len(active_transactions)
        pool_status = f"Занято: {total_used}, Всего: {engine.pool.size()}, Макс: {engine.pool.size() + engine.pool.overflow()}"
        
        threshold = engine.pool.size() * 0.8
        if total_used > threshold:
            logger.warning(f"Высокая загрузка пула соединений! {pool_status}")
        else:
            logger.debug(f"Соединение взято из пула. {pool_status}")
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
                if duration > 0.5:
                    logger.info(f"Транзакция завершена за {duration:.2f} сек (соединение {conn_id})")
        
        logger.debug(f"Соединение возвращено в пул. Активных: {len(active_transactions)}")
    except Exception as e:
        logger.error(f"Ошибка при возврате соединения: {e}")

SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False
    )
)

@contextlib.contextmanager
def timed_session():
    start = time.time()
    session = SessionLocal()
    try:
        yield session
        duration = time.time() - start
        if duration > 0.1:
            logger.info(f"Завершена транзакция БД за {duration:.3f} сек")
    except (DBAPIError, SQLAlchemyError) as e:
        logger.error(f"Ошибка БД ({time.time() - start:.3f} сек): {str(e)}")
        raise
    finally:
        session.close()

def get_db():
    start_time = time.time()
    db = SessionLocal()
    try:
        yield db
    except DBAPIError as e:
        logger.error(f"Ошибка БД: {str(e)}. Время: {time.time() - start_time:.3f} сек")
        raise
    finally:
        db.close()
