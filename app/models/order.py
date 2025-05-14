from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

from app.models.base import Direction, OrderStatus

class OrderBase(BaseModel):
    ticker: str
    qty: int
    direction: Direction

class LimitOrderBody(OrderBase):
    price: int
    type: str = "limit"

class MarketOrderBody(OrderBase):
    type: str = "market"

class OrderResponse(OrderBase):
    id: UUID
    user_id: UUID
    filled: int = 0
    status: OrderStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

class LimitOrder(OrderResponse):
    price: int
    type: str = "limit"

class MarketOrder(OrderResponse):
    type: str = "market"
from pydantic import BaseModel
from app.models.base import Direction


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"


class LimitOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int
    price: int


class MarketOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int


class LimitOrder(BaseModel):
    id: str
    status: OrderStatus
    user_id: str
    timestamp: datetime
    body: LimitOrderBody
    filled: int = 0


class MarketOrder(BaseModel):
    id: str
    status: OrderStatus
    user_id: str
    timestamp: datetime
    body: MarketOrderBody
