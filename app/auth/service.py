from uuid import uuid4
from typing import Dict
import secrets
import string

from app.models.user import User, UserRole
from app.core.logging import setup_logger

logger = setup_logger("app.auth.service")


async def create_user(user_data: Dict) -> User:
    user_id = uuid4()
    logger.debug(f"Generated user_id: {user_id}")

    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(8))
    api_key = f"key-{random_part}-{str(user_id)[:8]}"
    
    logger.info(f"Creating new user: id={user_id}, name={user_data['name']}")

    return User(
        id=user_id,
        name=user_data["name"],
        role=UserRole.USER,
        api_key=api_key,
    )
