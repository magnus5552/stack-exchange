from typing import List, Optional, Union
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.entities.order import OrderEntity, LimitOrderEntity, MarketOrderEntity
from app.models.base import OrderStatus, Direction
from app.models.order import LimitOrderBody, MarketOrderBody, LimitOrder, MarketOrder
from app.core.logging import setup_logger
from app.repositories.balance_repository import BalanceRepository
from fastapi import HTTPException, status


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db
        self.logger = setup_logger("app.repositories.order")
        self.balance_repo = BalanceRepository(db)

    def create_limit_order(self, user_id: UUID, body: LimitOrderBody) -> OrderEntity:
        order_id = uuid4()
        self.logger.info(f"Creating new limit order: id={order_id}, user={user_id}, ticker={body.ticker}")
        
        try:
            # Если это ордер на продажу (SELL), блокируем указанное количество инструментов
            # Если это ордер на покупку (BUY), блокируем сумму средств в RUB (qty * price)
            if body.direction == Direction.SELL:
                # Для SELL блокируем количество инструментов указанного тикера
                lock_ticker = body.ticker
                lock_amount = body.qty
            else:  # BUY
                # Для BUY блокируем рубли в количестве (qty * price)
                lock_ticker = "RUB"
                lock_amount = body.qty * body.price
                
            # Проверяем наличие и блокируем средства
            balance_locked = self.balance_repo.lock_balance(user_id, lock_ticker, lock_amount)
            if not balance_locked:
                self.logger.warning(f"Insufficient funds to lock for order: user={user_id}, ticker={lock_ticker}, amount={lock_amount}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient funds for {lock_ticker}"
                )
            
            # Создаем ордер
            order = LimitOrderEntity(
                id=order_id,
                user_id=user_id,
                direction=body.direction,
                ticker=body.ticker,
                qty=body.qty,
                price=body.price,
                status=OrderStatus.NEW,
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
            self.logger.info(f"Limit order created successfully: id={order_id}")
            return order
        except HTTPException as e:
            self.db.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Error creating limit order: {str(e)}")
            self.db.rollback()
            raise

    def create_market_order(self, user_id: UUID, body: MarketOrderBody) -> OrderEntity:
        order_id = uuid4()
        self.logger.info(f"Creating new market order: id={order_id}, user={user_id}, ticker={body.ticker}")
        
        try:
            # Для маркет-ордеров на продажу блокируем количество инструментов
            # Для маркет-ордеров на покупку блокировка не нужна, так как цена заранее неизвестна
            # и будет определена при исполнении ордера
            if body.direction == Direction.SELL:
                # Блокируем количество инструментов указанного тикера
                balance_locked = self.balance_repo.lock_balance(user_id, body.ticker, body.qty)
                if not balance_locked:
                    self.logger.warning(f"Insufficient funds to lock for market order: user={user_id}, ticker={body.ticker}, amount={body.qty}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient funds for {body.ticker}"
                    )
            
            order = MarketOrderEntity(
                id=order_id,
                user_id=user_id,
                direction=body.direction,
                ticker=body.ticker,
                qty=body.qty,
                status=OrderStatus.NEW,
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
            self.logger.info(f"Market order created successfully: id={order_id}")
            return order
        except HTTPException as e:
            self.db.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Error creating market order: {str(e)}")
            self.db.rollback()
            raise

    def get_by_id(self, order_id: UUID) -> Optional[OrderEntity]:
        self.logger.debug(f"Fetching order by ID: {order_id}")
        try:
            order = self.db.query(OrderEntity).filter(OrderEntity.id == order_id).first()
            if order:
                self.logger.debug(f"Found order: {order_id}, type={order.type}, status={order.status}")
            else:
                self.logger.debug(f"Order not found: {order_id}")
            return order
        except Exception as e:
            self.logger.error(f"Error fetching order {order_id}: {str(e)}")
            raise
    
    def get_all_by_user(self, user_id: UUID) -> List[OrderEntity]:
        self.logger.debug(f"Fetching all orders for user: {user_id}")
        try:
            orders = self.db.query(OrderEntity).filter(OrderEntity.user_id == user_id).all()
            self.logger.debug(f"Found {len(orders)} orders for user {user_id}")
            return orders
        except Exception as e:
            self.logger.error(f"Error fetching orders for user {user_id}: {str(e)}")
            raise
    
    def get_active_by_ticker(self, ticker: str, limit: int = 10) -> List[OrderEntity]:
        self.logger.debug(f"Fetching active orders for ticker: {ticker}, limit={limit}")
        try:
            orders = (
                self.db.query(OrderEntity)
                .filter(
                    OrderEntity.ticker == ticker,
                    OrderEntity.status.in_(
                        [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
                    ),
                )
                .limit(limit)
                .all()
            )
            self.logger.debug(f"Found {len(orders)} active orders for ticker {ticker}")
            return orders
        except Exception as e:
            self.logger.error(f"Error fetching active orders for ticker {ticker}: {str(e)}")
            raise
    
    def update_order_status(
        self, order_id: UUID, status: OrderStatus, filled: int = None
    ) -> Optional[OrderEntity]:
        self.logger.info(f"Updating order status: {order_id} to {status}, filled={filled}")
        try:
            order = self.get_by_id(order_id)
            if not order:
                self.logger.warning(f"Cannot update status: Order {order_id} not found")
                return None

            old_status = order.status
            order.status = status
            if filled is not None:
                order.filled = filled

            self.db.commit()
            self.db.refresh(order)
            self.logger.info(f"Order {order_id} status updated: {old_status} -> {status}")
            return order
        except Exception as e:
            self.logger.error(f"Error updating order status {order_id}: {str(e)}")
            self.db.rollback()
            raise
    
    def cancel_order(self, order_id: UUID) -> bool:
        self.logger.info(f"Cancelling order: {order_id}")
        try:
            order = self.get_by_id(order_id)
            if not order:
                self.logger.warning(f"Cannot cancel: Order {order_id} not found")
                return False

            if order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]:
                self.logger.warning(f"Cannot cancel order {order_id} with status {order.status}")
                return False

            # Разблокировка средств при отмене ордера
            if order.type == "limit":
                remaining_qty = order.qty - (order.filled or 0)
                if remaining_qty > 0:
                    # Для ордеров на продажу разблокируем инструменты
                    if order.direction == Direction.SELL:
                        unlock_ticker = order.ticker
                        unlock_amount = remaining_qty
                    # Для ордеров на покупку разблокируем рубли
                    else:  # BUY
                        unlock_ticker = "RUB"
                        unlock_amount = remaining_qty * order.price
                        
                    self.logger.info(f"Разблокировка средств для отмененного ордера: {order_id}, тикер={unlock_ticker}, количество={unlock_amount}")
                    self.balance_repo.unlock_balance(order.user_id, unlock_ticker, unlock_amount)
            
            # Для маркет-ордеров на продажу также разблокируем инструменты
            elif order.type == "market" and order.direction == Direction.SELL:
                remaining_qty = order.qty - (order.filled or 0)
                if remaining_qty > 0:
                    self.logger.info(f"Разблокировка инструментов для отмененного маркет-ордера: {order_id}, тикер={order.ticker}, количество={remaining_qty}")
                    self.balance_repo.unlock_balance(order.user_id, order.ticker, remaining_qty)
    
            order.status = OrderStatus.CANCELLED
            self.db.commit()
            self.logger.info(f"Order {order_id} cancelled successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {str(e)}")
            self.db.rollback()
            raise

    def to_model(self, entity: OrderEntity) -> Union[LimitOrder, MarketOrder]:
        if entity.type == "limit":
            body = LimitOrderBody(
                direction=entity.direction,
                ticker=entity.ticker,
                qty=entity.qty,
                price=entity.price,
            )
            return LimitOrder(
                id=str(entity.id),
                status=entity.status,
                user_id=str(entity.user_id),
                timestamp=entity.created_at,
                body=body,
                filled=entity.filled,
            )
        else:  # market
            body = MarketOrderBody(
                direction=entity.direction, ticker=entity.ticker, qty=entity.qty
            )
            return MarketOrder(
                id=str(entity.id),
                status=entity.status,
                user_id=str(entity.user_id),
                timestamp=entity.created_at,
                body=body,
            )
