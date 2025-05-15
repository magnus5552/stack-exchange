from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import time
from functools import lru_cache

from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.entities.user import UserEntity
from app.repositories.user_repository import UserRepository
from app.core.logging import setup_logger

logger = setup_logger("app.auth.dependencies")

# Кеширование активных пользователей для снижения нагрузки на БД
# Ключ: api_key, Значение: (пользователь, время добавления в кеш)
# Кеш действителен в течение 5 минут для активных пользователей
USER_CACHE: Dict[str, Tuple[UserEntity, datetime]] = {}
CACHE_TTL = timedelta(minutes=5)
CACHE_CLEANUP_INTERVAL = 60
last_cleanup = time.time()


def cleanup_user_cache():
    """Очистка устаревших записей в кеше пользователей"""
    global last_cleanup
    now = time.time()
    
    # Выполняем очистку не чаще, чем раз в минуту
    if now - last_cleanup < CACHE_CLEANUP_INTERVAL:
        return
        
    try:
        current_time = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in USER_CACHE.items() 
            if current_time - timestamp > CACHE_TTL
        ]
        
        for key in expired_keys:
            USER_CACHE.pop(key, None)
            
        if expired_keys:
            logger.debug(f"Удалено {len(expired_keys)} устаревших записей из кеша пользователей")
            
        last_cleanup = now
    except Exception as e:
        logger.error(f"Ошибка при очистке кеша пользователей: {e}")


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> UserEntity:
    """
    Оптимизированная функция получения текущего пользователя.
    Использует кеширование авторизованных пользователей для снижения нагрузки на БД.
    """
    client_ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path

    is_high_volume = any(path in endpoint for path in ['/api/v1/orders', '/api/v1/balances', '/api/v1/instruments'])
    
    if not authorization:
        if not is_high_volume:
            logger.warning(f"Unauthorized: No header from {client_ip} to {endpoint}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    parts = authorization.split()
    if len(parts) < 2 or parts[0].lower() != "token":
        if not is_high_volume:
            logger.warning(f"Invalid auth format from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication format" 
        )

    token = parts[1]
    
    if token in USER_CACHE:
        user, cache_time = USER_CACHE[token]
        if datetime.now() - cache_time < CACHE_TTL:
            return user
        USER_CACHE.pop(token, None)
    
    cleanup_user_cache()
    
    try:
        start_time = time.time()
        user_repo = UserRepository(db)
        user = user_repo.get_by_api_key(token, include_inactive=False)

        query_time = time.time() - start_time
        if query_time > 0.1:
            logger.warning(f"Slow auth query: {query_time:.3f}s for token ending with {token[-4:]}")

        if not user:
            if not is_high_volume:
                logger.warning(f"Invalid token from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid or expired token"
            )

        USER_CACHE[token] = (user, datetime.now())
        
        if not is_high_volume:
            logger.debug(f"User {user.id} authenticated")
        return user
        
    except SQLAlchemyError as e:
        logger.error(f"Database error during authentication: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )


@lru_cache(maxsize=128)
def is_admin_role(role: str) -> bool:
    """Кешированная проверка роли администратора"""
    return role == "ADMIN"


async def get_admin_user(
    request: Request,
    user: UserEntity = Depends(get_current_user)
) -> UserEntity:
    """Оптимизированная проверка привилегий администратора"""
    if not is_admin_role(user.role):
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        logger.warning(f"Access denied: User {user.id} to admin endpoint {endpoint}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin privileges required"
        )
    
    return user


CurrentUser = Depends(get_current_user)
AdminUser = Depends(get_admin_user)
