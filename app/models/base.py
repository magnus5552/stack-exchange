from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import Union, List, Dict, Any


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
    ticker: str
    amount: int
    price: int
    timestamp: datetime


class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"
