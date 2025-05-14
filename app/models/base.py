from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Ok(BaseModel):
    success: bool = True


class CreateOrderResponse(BaseModel):
    success: bool = True
    order_id: str


class Level(BaseModel):
    price: int
    qty: int


class L2OrderBook(BaseModel):
    bid_levels: List[Level]
    ask_levels: List[Level]


class Transaction(BaseModel):
    id: str
    ticker: str
    amount: int
    price: int
    buyer_order_id: str
    seller_order_id: str
    timestamp: datetime


class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"
