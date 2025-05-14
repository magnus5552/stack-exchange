from typing import List, Optional, Union
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.entities.order import OrderEntity, LimitOrderEntity, MarketOrderEntity
from app.models.base import OrderStatus
from app.models.order import LimitOrderBody, MarketOrderBody, LimitOrder, MarketOrder
from app.core.logging import setup_logger


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db
        self.logger = setup_logger("app.repositories.order")

    def create_limit_order(self, user_id: UUID, body: LimitOrderBody) -> OrderEntity:
        order_id = uuid4()
        self.logger.info(f"Creating new limit order: id={order_id}, user={user_id}, ticker={body.ticker}")
        
        try:
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
        except Exception as e:
            self.logger.error(f"Error creating limit order: {str(e)}")
            self.db.rollback()
            raise

    def create_market_order(self, user_id: UUID, body: MarketOrderBody) -> OrderEntity:
        order_id = uuid4()
        self.logger.info(f"Creating new market order: id={order_id}, user={user_id}, ticker={body.ticker}")
        
        try:
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
