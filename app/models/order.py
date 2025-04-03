from datetime import datetime
from enum import Enum

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
