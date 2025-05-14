from fastapi import APIRouter, Query, Depends, Request
from sqlalchemy.orm import Session
import time

from app.auth.service import create_user
from app.models import user, instrument, base
from app.core.database import get_db
from app.services.instrument_service import InstrumentService
from app.services.exchange_service import ExchangeService
from app.core.logging import setup_logger

logger = setup_logger("app.routers.public")
router = APIRouter(tags=["public"])


@router.post("/register", response_model=user.User)
async def register(request: Request, new_user: user.NewUser, db: Session = Depends(get_db)):
    """Регистрация нового пользователя в системе"""
    client_ip = request.client.host if request.client else "unknown"
    start_time = time.time()
    
    logger.info(f"Registration request from {client_ip} for user: {new_user.name}")
    
    try:
        user_model = await create_user({"name": new_user.name})

        # Создаем пользователя в БД
        from app.repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        user_entity = user_repo.create(
            name=user_model.name, api_key=user_model.api_key, role=user_model.role
        )
        
        elapsed = time.time() - start_time
        logger.info(f"User registered successfully: id={user_model.id}, name={user_model.name}, time={elapsed:.2f}s")
        return user_model
    
    except Exception as e:
        logger.error(f"Failed to register user {new_user.name} from {client_ip}: {str(e)}")
        raise


@router.get("/instrument", response_model=list[instrument.Instrument])
async def list_instruments(request: Request, db: Session = Depends(get_db)):
    """Получение списка доступных инструментов"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Fetching instruments list from {client_ip}")
    
    try:
        service = InstrumentService(db)
        instruments = await service.get_all_instruments()
        logger.info(f"Returned {len(instruments)} instruments to {client_ip}")
        return instruments
    except Exception as e:
        logger.error(f"Error fetching instruments for {client_ip}: {str(e)}")
        raise


@router.get("/orderbook/{ticker}", response_model=base.L2OrderBook)
async def get_orderbook(
    request: Request,
    ticker: str, 
    limit: int = Query(10, gt=0, le=25), 
    db: Session = Depends(get_db)
):
    """Получение стакана заявок по указанному инструменту"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Orderbook request from {client_ip} for {ticker} with limit {limit}")
    
    try:
        service = ExchangeService(db)
        orderbook = await service.get_orderbook(ticker, limit)
        
        bid_count = len(orderbook.bid_levels)
        ask_count = len(orderbook.ask_levels)
        logger.info(f"Returned orderbook for {ticker} with {bid_count} bids and {ask_count} asks to {client_ip}")
        
        return orderbook
    except Exception as e:
        logger.error(f"Error fetching orderbook for {ticker} from {client_ip}: {str(e)}")
        raise


@router.get("/transactions/{ticker}", response_model=list[base.Transaction])
async def get_transaction_history(
    request: Request,
    ticker: str, 
    limit: int = Query(10, gt=0, le=100), 
    db: Session = Depends(get_db)
):
    """Получение истории сделок по указанному инструменту"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Transaction history request from {client_ip} for {ticker} with limit {limit}")
    
    try:
        service = ExchangeService(db)
        transactions = await service.get_transaction_history(ticker, limit)
        
        logger.info(f"Returned {len(transactions)} transactions for {ticker} to {client_ip}")
        return transactions
    except Exception as e:
        logger.error(f"Error fetching transactions for {ticker} from {client_ip}: {str(e)}")
        raise
