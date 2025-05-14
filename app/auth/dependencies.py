from typing import Optional

from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.entities.user import UserEntity
from app.repositories.user_repository import UserRepository
from app.core.logging import setup_logger

logger = setup_logger("app.auth.dependencies")


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> UserEntity:
    client_ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    
    if not authorization:
        logger.warning(f"Unauthorized access attempt from {client_ip} to {endpoint}: No authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    parts = authorization.split()
    if parts[0].lower() != "token":
        logger.warning(f"Invalid auth scheme from {client_ip} to {endpoint}: {parts[0]}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
        )

    if len(parts) == 1:
        logger.warning(f"Missing token from {client_ip} to {endpoint}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    token = parts[1]
    user_repo = UserRepository(db)
    # Получаем только активных пользователей
    user = user_repo.get_by_api_key(token, include_inactive=False)

    if not user:
        logger.warning(f"Invalid token or inactive user from {client_ip} to {endpoint}: {token[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid, expired token or deactivated user"
        )

    logger.info(f"User {user.id} ({user.name}) authenticated from {client_ip} to {endpoint}")
    return user


async def get_admin_user(
    request: Request,
    user: UserEntity = Depends(get_current_user)
) -> UserEntity:
    client_ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    
    if user.role != "ADMIN":
        logger.warning(f"Access denied: User {user.id} ({user.name}) tried to access admin endpoint {endpoint} from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    
    logger.info(f"Admin {user.id} ({user.name}) accessed {endpoint} from {client_ip}")
    return user


CurrentUser = Depends(get_current_user)
AdminUser = Depends(get_admin_user)
