from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from app.entities.base import BaseEntity
from app.models.base import Direction, OrderStatus


class OrderEntity(BaseEntity):
    __tablename__ = "orders"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    direction = Column(Enum(Direction), nullable=False)
    ticker = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    price = Column(Integer, nullable=True)
    filled = Column(Integer, default=0)
    status = Column(Enum(OrderStatus), default=OrderStatus.NEW, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'order',
    }


class LimitOrderEntity(OrderEntity):
    __mapper_args__ = {
        'polymorphic_identity': 'limit',
    }

class MarketOrderEntity(OrderEntity):
    __mapper_args__ = {
        'polymorphic_identity': 'market',
    }