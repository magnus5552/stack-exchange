from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.order import OrderEntity, LimitOrderEntity, MarketOrderEntity
from app.models.base import OrderStatus
from app.models.order import LimitOrderBody, MarketOrderBody, LimitOrder, MarketOrder


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_limit_order(self, user_id: UUID, body: LimitOrderBody) -> OrderEntity:
        order = LimitOrderEntity(
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
        return order

    def create_market_order(self, user_id: UUID, body: MarketOrderBody) -> OrderEntity:
        order = MarketOrderEntity(
            user_id=user_id,
            direction=body.direction,
            ticker=body.ticker,
            qty=body.qty,
            status=OrderStatus.NEW,
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_by_id(self, order_id: UUID) -> Optional[OrderEntity]:
        return self.db.query(OrderEntity).filter(OrderEntity.id == order_id).first()

    def get_all_by_user(self, user_id: UUID) -> List[OrderEntity]:
        return self.db.query(OrderEntity).filter(OrderEntity.user_id == user_id).all()

    def get_active_by_ticker(self, ticker: str, limit: int = 10) -> List[OrderEntity]:
        return (
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

    def update_order_status(
        self, order_id: UUID, status: OrderStatus, filled: int = None
    ) -> Optional[OrderEntity]:
        order = self.get_by_id(order_id)
        if order:
            order.status = status
            if filled is not None:
                order.filled = filled
            self.db.commit()
            self.db.refresh(order)
        return order

    def cancel_order(self, order_id: UUID) -> bool:
        order = self.get_by_id(order_id)
        if order and order.status in [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]:
            order.status = OrderStatus.CANCELLED
            self.db.commit()
            return True
        return False

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
