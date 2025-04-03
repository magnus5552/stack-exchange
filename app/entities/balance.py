from sqlalchemy import Column, UUID, Integer, ForeignKey, CheckConstraint
from sqlalchemy.schema import PrimaryKeyConstraint
from app.entities.base import BaseEntity


class BalanceEntity(BaseEntity):
    __tablename__ = "balances"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"),
                           nullable=False)
    amount = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "instrument_id"),
        CheckConstraint("amount >= 0", name="non_negative_amount"),
    )
