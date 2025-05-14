from pydantic import BaseModel
from uuid import UUID
from uuid import UUID

from pydantic import BaseModel


class Deposit(BaseModel):
    user_id: UUID
    ticker: str
    amount: int

class Withdraw(BaseModel):
    user_id: UUID
    ticker: str
    amount: int
from pydantic import BaseModel


class Deposit(BaseModel):
    user_id: UUID
    ticker: str
    amount: int


class Withdraw(BaseModel):
    user_id: UUID
    ticker: str
    amount: int
