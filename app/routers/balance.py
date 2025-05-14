from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import Dict

from app.core.database import get_db
from app.auth.dependencies import CurrentUser
from app.services.balance_service import BalanceService
from app.entities.user import UserEntity
from app.core.logging import setup_logger

logger = setup_logger("app.routers.balance")
router = APIRouter(tags=["balance"])


@router.get("", response_model=Dict[str, int])
async def get_balances(
    request: Request,
    user: UserEntity = CurrentUser,
    db: Session = Depends(get_db)
):
    """Получение балансов пользователя по всем инструментам"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Balance request: user={user.id}, from={client_ip}")
    
    try:
        service = BalanceService(db)
        balances = await service.get_user_balances(user.id)
        
        # Логируем только количество инструментов, не сами суммы (для безопасности)
        logger.info(f"Returned balances for {len(balances)} instruments to user {user.id}")
        return balances
    except Exception as e:
        logger.error(f"Failed to get balances for user {user.id}: {str(e)}")
        raise