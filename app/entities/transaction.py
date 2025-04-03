from sqlalchemy import Column, UUID, Integer, DateTime, ForeignKey, \
    CheckConstraint, func
from app.entities.base import BaseEntity


class TransactionEntity(BaseEntity):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True)
    buyer_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"),
                            nullable=False)
    seller_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"),
                             nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"),
                           nullable=False)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_transaction_quantity"),
    )