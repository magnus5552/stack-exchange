from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.transaction import TransactionEntity
from app.models.base import Transaction


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        ticker: str,
        amount: int,
        price: int,
        buyer_order_id: UUID,
        seller_order_id: UUID,
    ) -> TransactionEntity:
        transaction = TransactionEntity(
            ticker=ticker,
            amount=amount,
            price=price,
            buyer_order_id=buyer_order_id,
            seller_order_id=seller_order_id,
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_by_ticker(self, ticker: str, limit: int = 10) -> List[TransactionEntity]:
        return (
            self.db.query(TransactionEntity)
            .filter(TransactionEntity.ticker == ticker)
            .order_by(TransactionEntity.timestamp.desc())
            .limit(limit)
            .all()
        )

    def to_model(self, entity: TransactionEntity) -> Transaction:
        return Transaction(
            ticker=entity.ticker,
            amount=entity.amount,
            price=entity.price,
            timestamp=entity.timestamp,
        )
