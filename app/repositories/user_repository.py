from uuid import UUID, uuid4
from typing import Optional, List
from sqlalchemy.orm import Session
from app.entities.user import UserEntity
from app.models.user import User, UserRole
from app.core.logging import setup_logger


class UserRepository:
    def __init__(self, db: Session):
        self.db = db
        self._model = UserEntity  # Добавляем атрибут _model
        self.logger = setup_logger("app.repositories.user")

    def create(
        self, name: str, api_key: str, role: UserRole = UserRole.USER
    ) -> UserEntity:
        """Создает нового пользователя в БД"""
        user_id = uuid4()
        self.logger.info(f"Creating new user in DB: name={name}, role={role}")
        
        try:
            db_user = UserEntity(
                id=user_id,
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

    def get_by_id(self, user_id: UUID) -> Optional[UserEntity]:
        """Получает пользователя по ID"""
        self.logger.debug(f"Fetching user by ID: {user_id}")
        user = self.db.query(UserEntity).filter(UserEntity.id == user_id).first()
        
        if user:
            self.logger.debug(f"Found user: {user_id}")
        else:
            self.logger.debug(f"User not found: {user_id}")
            
        return user

    def get_by_api_key(self, api_key: str) -> Optional[UserEntity]:
        """Получает пользователя по API ключу"""
        # Скрываем полный API ключ в логах для безопасности
        masked_key = f"{api_key[:8]}..." if len(api_key) > 8 else "***"
        self.logger.debug(f"Fetching user by API key: {masked_key}")
        
        user = self.db.query(UserEntity).filter(UserEntity.api_key == api_key).first()
        
        if user:
            self.logger.debug(f"Found user by API key: id={user.id}")
        else:
            self.logger.debug(f"User not found by API key: {masked_key}")
            
        return user

    def delete(self, user_id: UUID) -> Optional[UserEntity]:
        """Удаляет пользователя по ID"""
        self.logger.info(f"Deleting user: {user_id}")
        
        try:
            user = self.get_by_id(user_id)
            if user:
                self.db.delete(user)
                self.db.commit()
                self.logger.info(f"User {user_id} deleted successfully")
            else:
                self.logger.warning(f"Delete failed: User {user_id} not found")
                
            return user
        except Exception as e:
            self.logger.error(f"Error deleting user {user_id}: {str(e)}")
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
