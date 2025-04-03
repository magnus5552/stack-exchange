from sqlalchemy import (
    Column, UUID, Integer, DateTime, func,
    ForeignKey, CheckConstraint, Enum
)

from app.entities.base import BaseEntity
from app.models.order import OrderStatus, Direction, OrderType


class OrderEntity(BaseEntity):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"),
                           nullable=False)
    type = Column(Enum(OrderType, name="order_type_enum"), nullable=False)
    direction = Column(Enum(Direction, name="direction_enum"), nullable=False)
    price = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=False)
    filled = Column(Integer, default=0)
    status = Column(Enum(OrderStatus, name="order_status_enum"),
                    nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_quantity"),
        CheckConstraint("filled <= quantity",
                        name="filled_less_than_quantity"),
        CheckConstraint(
            "(type = 'LIMIT' AND price IS NOT NULL) OR (type = 'MARKET' AND price IS NULL)",
            name="price_constraint_for_order_type"
        ),
    )
