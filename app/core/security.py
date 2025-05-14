from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi import Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.entities.user import UserEntity
from app.repositories.user_repository import UserRepository


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> UserEntity:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    parts = authorization.split()
    if parts[0].lower() != "token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme"
        )
    
    if len(parts) == 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    token = parts[1]
    user_repo = UserRepository(db)
    user = user_repo.get_by_api_key(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return user


async def get_admin_user(
    user: UserEntity = Depends(get_current_user)
) -> UserEntity:
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user