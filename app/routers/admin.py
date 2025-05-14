from fastapi import APIRouter, Depends, Path, Body, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.auth.dependencies import AdminUser
from app.services.user_service import UserService
from app.services.instrument_service import InstrumentService
from app.services.balance_service import BalanceService
from app.entities.user import UserEntity
from app.models import user, instrument, balance, base
from app.core.logging import setup_logger

logger = setup_logger("app.routers.admin")
router = APIRouter(tags=["admin"])


@router.delete("/user/{user_id}", response_model=user.User)
async def delete_user(
    request: Request,
    user_id: UUID = Path(...),
    admin: UserEntity = AdminUser,
    db: Session = Depends(get_db)
):
    """Удаление пользователя (только для администраторов)"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Admin {admin.id} ({admin.name}) requested to delete user {user_id} from {client_ip}")
    
    try:
        service = UserService(db)
        deleted_user = await service.delete_user(user_id)
        
        logger.info(f"User {user_id} successfully deleted by admin {admin.id}")
        return deleted_user
    except Exception as e:
        logger.error(f"Failed to delete user {user_id} by admin {admin.id}: {str(e)}")
        raise


@router.post("/instrument", response_model=base.Ok)
async def add_instrument(
    request: Request,
    new_instrument: instrument.Instrument,
    admin: UserEntity = AdminUser,
    db: Session = Depends(get_db)
):
    """Добавление нового инструмента (только для администраторов)"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Admin {admin.id} adding new instrument: {new_instrument.ticker} from {client_ip}")
    
    try:
        service = InstrumentService(db)
        result = await service.add_instrument(new_instrument)
        
        logger.info(f"Instrument {new_instrument.ticker} successfully added by admin {admin.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to add instrument {new_instrument.ticker} by admin {admin.id}: {str(e)}")
        raise


@router.delete("/instrument/{ticker}", response_model=base.Ok)
async def delete_instrument(
    request: Request,
    ticker: str = Path(...),
    admin: UserEntity = AdminUser,
    db: Session = Depends(get_db)
):
    """Удаление инструмента (только для администраторов)"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Admin {admin.id} deleting instrument: {ticker} from {client_ip}")
    
    try:
        service = InstrumentService(db)
        result = await service.delete_instrument(ticker)
        
        logger.info(f"Instrument {ticker} successfully deleted by admin {admin.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to delete instrument {ticker} by admin {admin.id}: {str(e)}")
        raise


@router.post("/balance/deposit", response_model=base.Ok)
async def deposit(
    request: Request,
    deposit_data: balance.Deposit,
    admin: UserEntity = AdminUser,
    db: Session = Depends(get_db)
):
    """Пополнение баланса пользователя (только для администраторов)"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        f"Admin {admin.id} depositing {deposit_data.amount} {deposit_data.ticker} "
        f"to user {deposit_data.user_id} from {client_ip}"
    )
    
    try:
        service = BalanceService(db)
        result = await service.deposit(
            deposit_data.user_id,
            deposit_data.ticker,
            deposit_data.amount
        )
        
        logger.info(
            f"Successfully deposited {deposit_data.amount} {deposit_data.ticker} "
            f"to user {deposit_data.user_id} by admin {admin.id}"
        )
        return result
    except Exception as e:
        logger.error(
            f"Failed to deposit {deposit_data.amount} {deposit_data.ticker} "
            f"to user {deposit_data.user_id} by admin {admin.id}: {str(e)}"
        )
        raise


@router.post("/balance/withdraw", response_model=base.Ok)
async def withdraw(
    request: Request,
    withdraw_data: balance.Withdraw,
    admin: UserEntity = AdminUser,
    db: Session = Depends(get_db)
):
    """Списание средств с баланса пользователя (только для администраторов)"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        f"Admin {admin.id} withdrawing {withdraw_data.amount} {withdraw_data.ticker} "
        f"from user {withdraw_data.user_id} from {client_ip}"
    )
    
    try:
        service = BalanceService(db)
        result = await service.withdraw(
            withdraw_data.user_id,
            withdraw_data.ticker,
            withdraw_data.amount
        )
        
        logger.info(
            f"Successfully withdrew {withdraw_data.amount} {withdraw_data.ticker} "
            f"from user {withdraw_data.user_id} by admin {admin.id}"
        )
        return result
    except Exception as e:
        logger.error(
            f"Failed to withdraw {withdraw_data.amount} {withdraw_data.ticker} "
            f"from user {withdraw_data.user_id} by admin {admin.id}: {str(e)}"
        )
        raise