from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import logging

from app.core.config import settings

# Настройка логгера для пула соединений
logger = logging.getLogger("sqlalchemy.pool")

# Оптимизация параметров пула соединений:
# - pool_size: оптимальный размер основного пула
# - max_overflow: доп. соединения при большой нагрузке
# - pool_pre_ping: проверка "живых" соединений перед использованием
# - pool_recycle: предотвращение разрыва соединений сервером БД
# - pool_timeout: таймаут ожидания доступного соединения
engine = create_engine(
    settings.DB_CONN_STRING,
    echo=settings.DB_ECHO,
    poolclass=QueuePool,
    pool_size=25,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=30
)

# Мониторинг использования пула соединений
@event.listens_for(engine, "checkout")
def checkout_handler(dbapi_conn, conn_record, conn_proxy):
    logger.debug(f"Соединение взято из пула. Статус пула: {engine.pool.status()}")

@event.listens_for(engine, "checkin")
def checkin_handler(dbapi_conn, conn_record):
    logger.debug(f"Соединение возвращено в пул.")

# Создание фабрики сессий с привязкой к потоку для предотвращения 
# проблем с многопоточностью и повторным использованием сессий
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def get_db():
    """
    Функция предоставления сессии БД с автоматическим управлением соединениями.
    Использует привязку к текущему потоку/запросу и закрывает сессию после использования.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # Обязательно закрываем сессию, возвращая соединение в пул
        db.close()
