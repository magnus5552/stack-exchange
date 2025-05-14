from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.balance import BalanceEntity


class BalanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_and_ticker(
        self, user_id: UUID, ticker: str
    ) -> Optional[BalanceEntity]:
        return (
            self.db.query(BalanceEntity)
            .filter(BalanceEntity.user_id == user_id, BalanceEntity.ticker == ticker)
            .first()
        )

    def get_all_by_user(self, user_id: UUID) -> List[BalanceEntity]:
        return (
            self.db.query(BalanceEntity).filter(BalanceEntity.user_id == user_id).all()
        )

    def update_balance(self, user_id: UUID, ticker: str, amount: int) -> BalanceEntity:
        balance = self.get_by_user_and_ticker(user_id, ticker)

        if balance:
            balance.amount += amount
        else:
            balance = BalanceEntity(user_id=user_id, ticker=ticker, amount=amount)
            self.db.add(balance)

        self.db.commit()
        self.db.refresh(balance)
        return balance
