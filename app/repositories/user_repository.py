from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.logging import setup_logger
from app.entities.user import UserEntity
from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db
        self._model = UserEntity  # Добавляем атрибут _model
        self.logger = setup_logger("app.repositories.user")

    def create(self, name: str, api_key: str, role: UserRole = UserRole.USER, user_id: UUID = None) -> UserEntity:
        """
        Создает нового пользователя в БД

        Args:
            name: Имя пользователя
            api_key: API ключ пользователя
            role: Роль пользователя
            user_id: UUID пользователя (если None, будет сгенерирован новый)
        """
        if user_id is None:
            user_id = uuid4()

        self.logger.info(f"Creating new user in DB: id={user_id}, name={name}, role={role}")
        
        try:
            db_user = UserEntity(id=user_id,
                name=name, 
                api_key=api_key, 
                role=role.value if hasattr(role, 'value') else str(role),
                is_active=True
            )
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            
            self.logger.info(f"User created successfully: id={user_id}")
            return db_user
        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}")
            self.db.rollback()
            raise

    def get_by_id(self, user_id: UUID, include_inactive: bool = False) -> Optional[UserEntity]:
        """
        Получает пользователя по ID

        Args:
            user_id: Идентификатор пользователя
            include_inactive: Если True, возвращает также неактивных пользователей
        """
        self.logger.debug(f"Fetching user by ID: {user_id}, include_inactive={include_inactive}")

        query = self.db.query(UserEntity).filter(UserEntity.id == user_id)

        if not include_inactive:
            query = query.filter(UserEntity.is_active == True)

        user = query.first()

        if user:
            status = "active" if user.is_active else "inactive"
            self.logger.debug(f"Found {status} user: {user_id}")
        else:
            status_text = "active" if not include_inactive else ""
            self.logger.debug(f"{status_text} User not found: {user_id}")
            
        return user

    def get_by_api_key(self, api_key: str, include_inactive: bool = False) -> Optional[UserEntity]:
        """
        Получает пользователя по API ключу

        Args:
            api_key: API ключ пользователя
            include_inactive: Если True, возвращает также неактивных пользователей
        """
        # Скрываем полный API ключ в логах для безопасности
        masked_key = f"{api_key[:8]}..." if len(api_key) > 8 else "***"
        self.logger.debug(f"Fetching user by API key: {masked_key}, include_inactive={include_inactive}")

        query = self.db.query(UserEntity).filter(UserEntity.api_key == api_key)

        if not include_inactive:
            query = query.filter(UserEntity.is_active == True)

        user = query.first()

        if user:
            status = "active" if user.is_active else "inactive"
            self.logger.debug(f"Found {status} user by API key: id={user.id}")
        else:
            status_text = "active" if not include_inactive else ""
            self.logger.debug(f"{status_text} User not found by API key: {masked_key}")
            
        return user

    def delete(self, user_id: UUID) -> Optional[UserEntity]:
        """
        Деактивирует пользователя по ID (мягкое удаление)

        Вместо физического удаления записи из БД, помечает пользователя как неактивного.
        Это позволяет сохранить связанные данные и избежать нарушения ограничений внешнего ключа.
        """
        self.logger.info(f"Deactivating user: {user_id}")

        try:
            user = self.get_by_id(user_id)
            if not user:
                self.logger.warning(f"Deactivation failed: User {user_id} not found")
                return None

            # Если пользователь уже неактивен
            if not user.is_active:
                self.logger.info(f"User {user_id} is already inactive")
                return user

            # Мягкое удаление - устанавливаем флаг is_active в False
            user.is_active = False
            self.db.commit()
            self.db.refresh(user)
            self.logger.info(f"User {user_id} deactivated successfully")

            return user
        except Exception as e:
            self.logger.error(f"Error deactivating user {user_id}: {str(e)}")
            self.db.rollback()
            raise

    def to_model(self, entity: UserEntity) -> User:
        """Преобразует сущность в модель пользователя"""
        self.logger.debug(f"Converting user entity to model: id={entity.id}")
        return User(
            id=entity.id, 
            name=entity.name, 
            role=entity.role, 
            api_key=entity.api_key
        )
