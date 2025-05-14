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

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Получает информацию о пользователе по ID"""
        self.logger.info(f"Getting user by id: {user_id}")
        
        user = self.repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User with id {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )
            
        self.logger.debug(f"User found: {user_id}, name={user.name}, role={user.role}")
        return self.repository.to_model(user)

    async def delete_user(self, user_id: UUID) -> User:
        """Удаляет пользователя по ID"""
        self.logger.info(f"Deleting user: {user_id}")
        
        user = self.repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User with id {user_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

        try:
            user_model = self.repository.to_model(user)
            self.repository.delete(user_id)
            self.logger.info(f"User deleted successfully: {user_id}")
            return user_model
        except Exception as e:
            self.logger.error(f"Failed to delete user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting user: {str(e)}",
            )
