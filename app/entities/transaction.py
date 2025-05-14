from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.entities.base import BaseEntity


class TransactionEntity(BaseEntity):
    __tablename__ = "transactions"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    ticker = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    buyer_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    seller_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)