from typing import List, Union
from fastapi import APIRouter, Depends, Path, Body, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.auth.dependencies import CurrentUser
from app.services.exchange_service import ExchangeService
from app.entities.user import UserEntity
from app.models import order, base
from app.core.logging import setup_logger

logger = setup_logger("app.routers.order")
router = APIRouter(tags=["order"])


@router.post("", response_model=base.CreateOrderResponse)
async def create_order(
    request: Request,
    body: Union[order.LimitOrderBody, order.MarketOrderBody] = Body(...),
    user: UserEntity = CurrentUser,
    db: Session = Depends(get_db),
):
    """Создание нового ордера (лимитного или рыночного)"""
    client_ip = request.client.host if request.client else "unknown"
    
    order_type = "limit" if isinstance(body, order.LimitOrderBody) else "market"
    price_info = f"price={body.price}" if hasattr(body, 'price') else "market price"
    
    logger.info(
        f"Order creation request: user={user.id}, type={order_type}, "
        f"ticker={body.ticker}, direction={body.direction}, "
        f"qty={body.qty}, {price_info}, from={client_ip}"
    )
    
    try:
        service = ExchangeService(db)

        # Определяем тип ордера и вызываем соответствующий метод
        if isinstance(body, order.LimitOrderBody):
            order_id = await service.create_limit_order(user.id, body)
        else:
            order_id = await service.create_market_order(user.id, body)

        logger.info(f"Order created successfully: order_id={order_id}, user_id={user.id}")
        return base.CreateOrderResponse(order_id=order_id)
    except Exception as e:
        logger.error(f"Failed to create order for user {user.id}: {str(e)}")
        raise


@router.get("", response_model=List[Union[order.LimitOrder, order.MarketOrder]])
async def list_orders(
    request: Request,
    user: UserEntity = CurrentUser, 
    db: Session = Depends(get_db)
):
    """Получение списка ордеров пользователя"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"List orders request: user={user.id}, from={client_ip}")
    
    try:
        service = ExchangeService(db)
        orders = await service.get_user_orders(user.id)
        
        logger.info(f"Returned {len(orders)} orders for user {user.id}")
        return orders
    except Exception as e:
        logger.error(f"Failed to list orders for user {user.id}: {str(e)}")
        raise


@router.get("/{order_id}", response_model=Union[order.LimitOrder, order.MarketOrder])
async def get_order(
    request: Request,
    order_id: UUID = Path(...),
    user: UserEntity = CurrentUser,
    db: Session = Depends(get_db),
):
    """Получение информации о конкретном ордере"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Get order info request: order_id={order_id}, user={user.id}, from={client_ip}")
    
    try:
        service = ExchangeService(db)
        order_info = await service.get_order(order_id)
        
        logger.info(f"Order {order_id} details returned to user {user.id}")
        return order_info
    except Exception as e:
        logger.error(f"Failed to get order {order_id} for user {user.id}: {str(e)}")
        raise


@router.delete("/{order_id}", response_model=base.Ok)
async def cancel_order(
    request: Request,
    order_id: UUID = Path(...),
    user: UserEntity = CurrentUser,
    db: Session = Depends(get_db),
):
    """Отмена ордера"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Cancel order request: order_id={order_id}, user={user.id}, from={client_ip}")
    
    try:
        service = ExchangeService(db)
        await service.cancel_order(user.id, order_id)
        
        logger.info(f"Order {order_id} cancelled successfully by user {user.id}")
        return base.Ok()
    except Exception as e:
        logger.error(f"Failed to cancel order {order_id} for user {user.id}: {str(e)}")
        raise
