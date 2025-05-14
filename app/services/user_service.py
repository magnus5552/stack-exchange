from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.core.logging import setup_logger


class UserService:
    def __init__(self, db: Session):
        self.repository = UserRepository(db)
        self.logger = setup_logger("app.services.user")

    async def get_user(self, user_id: UUID, include_inactive: bool = False) -> Optional[User]:
        """
        Получает информацию о пользователе по ID

        Args:
            user_id: Идентификатор пользователя
            include_inactive: Если True, возвращает также неактивных пользователей
        """
        self.logger.info(f"Getting user by id: {user_id}, include_inactive={include_inactive}")

        user = self.repository.get_by_id(user_id, include_inactive=include_inactive)
        if not user:
            status_text = "active" if not include_inactive else ""
            self.logger.warning(f"{status_text} User with id {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

        user_status = "active" if user.is_active else "inactive"
        self.logger.debug(f"User found: {user_id}, name={user.name}, role={user.role}, status={user_status}")
        return self.repository.to_model(user)

    async def delete_user(self, user_id: UUID) -> User:
        """
        Деактивирует пользователя по ID (мягкое удаление)

        Не удаляет пользователя физически из базы данных, а помечает его как неактивного.
        Это сохраняет целостность данных и связи с другими таблицами.
        """
        self.logger.info(f"Deactivating user: {user_id}")

        user = self.repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User with id {user_id} not found for deactivation")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

        # Проверка, не является ли пользователь администратором
        if user.role == "ADMIN":
            self.logger.warning(f"Attempt to deactivate admin user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin users cannot be deleted",
            )

        try:
            deactivated_user = self.repository.delete(user_id)
            if not deactivated_user:
                self.logger.error(f"Failed to deactivate user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to deactivate user",
                )

            user_model = self.repository.to_model(deactivated_user)
            self.logger.info(f"User deactivated successfully: {user_id}")
            return user_model
        except HTTPException:
            # Пробрасываем уже созданные HTTP исключения
            raise
        except Exception as e:
            self.logger.error(f"Failed to deactivate user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deactivating user: {str(e)}",
        )
