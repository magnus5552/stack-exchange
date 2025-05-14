import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func, Enum
from sqlalchemy.dialects.postgresql import UUID
from app.entities.base import BaseEntity
from app.models.user import UserRole


class UserEntity(BaseEntity):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    role = Column(String(10), nullable=False, default="USER")
    api_key = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
