from datetime import timedelta
from uuid import uuid4

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User, UserRole


async def create_user(user_data: dict) -> User:
    # В реальном приложении здесь бы сохраняли пользователя в БД
    user_id = uuid4()
    token = create_access_token(
        data={"sub": user_data["name"], "user_id": str(user_id)},
    )

    return User(
        id=user_id,
        name=user_data["name"],
        role=UserRole.USER,
        api_key=token,
    )
