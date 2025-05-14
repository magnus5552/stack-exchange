from sqlalchemy import Column, Integer, String, Boolean, DateTime, CheckConstraint, func
from app.entities.base import BaseEntity


class InstrumentEntity(BaseEntity):
    __tablename__ = "instruments"
    __table_args__ = (
        CheckConstraint("ticker ~ '^[A-Z]{2,10}$'", name="ticker_format_check"),
        {"extend_existing": True}
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    ticker = Column(String(10), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())