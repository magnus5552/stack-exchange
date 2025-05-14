from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.entities.base import BaseEntity


class BalanceEntity(BaseEntity):
    __tablename__ = "balances"
    __table_args__ = (
        UniqueConstraint('user_id', 'ticker', name='uix_user_ticker'),
        {"extend_existing": True}
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ticker = Column(String(10), nullable=False)
    amount = Column(Integer, default=0, nullable=False)