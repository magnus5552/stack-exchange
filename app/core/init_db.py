import uuid
from sqlalchemy.orm import Session
from app.entities.base import BaseEntity
from app.core.database import engine
from app.repositories.user_repository import UserRepository
from app.models.user import UserRole
from app.core.logging import setup_logger

logger = setup_logger("app.core.init_db")


def init_database():
    """Инициализирует базу данных и создаёт таблицы"""
    logger.info("Инициализация базы данных...")
    
    try:
        # Создаем все таблицы
        BaseEntity.metadata.create_all(bind=engine)
        logger.info("Таблицы базы данных успешно созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц базы данных: {str(e)}", exc_info=True)
        raise


from app.core.config import settings

def create_admin_user(db: Session) -> str:
    logger.info("Проверка наличия администратора в системе...")
    
    try:
        repo = UserRepository(db)

        admin = db.query(repo._model).filter_by(role=UserRole.ADMIN).first()

        if admin:
            logger.info(f"Администратор уже существует: id={admin.id}, name={admin.name}")
            logger.debug(f"Используем существующий API ключ администратора: {admin.api_key}")
            return admin.api_key

        logger.info("Администратор не найден. Создание нового администратора...")
        admin_id = uuid.uuid4()
        
        # Используем предустановленный токен администратора, если он задан
        if settings.ADMIN_TOKEN:
            api_key = settings.ADMIN_TOKEN
            logger.info("Используется предустановленный токен администратора из настроек")
        else:
            api_key = f"admin-key-{str(admin_id)[:8]}"
            logger.info("Предустановленный токен администратора не задан, генерируется автоматически")

        admin = repo.create(name="Admin", api_key=api_key, role=UserRole.ADMIN)
        
        logger.info(f"Администратор успешно создан: id={admin.id}, API ключ={api_key}")
        
        return api_key
    except Exception as e:
        logger.error(f"Ошибка при создании администратора: {str(e)}", exc_info=True)
        raise
