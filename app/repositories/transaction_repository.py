from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.logging import setup_logger
from app.entities.transaction import TransactionEntity
from app.models.base import Transaction


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db
        self.logger = setup_logger("app.repositories.transaction")
        
    def create(self, ticker: str, amount: int, price: int, buyer_order_id: UUID, seller_order_id: UUID) -> TransactionEntity:
        """
        Создает новую транзакцию
        
        Args:
            ticker: Тикер инструмента
            amount: Количество
            price: Цена
            buyer_order_id: ID ордера покупателя
            seller_order_id: ID ордера продавца
        """
        transaction_id = uuid4()
        self.logger.info(f"Creating transaction: id={transaction_id}, ticker={ticker}, amount={amount}, price={price}")
        
        try:
            transaction = TransactionEntity(
                id=transaction_id,
                ticker=ticker, 
                amount=amount,
                price=price,
                buyer_order_id=buyer_order_id,
                seller_order_id=seller_order_id
            )
            self.db.add(transaction)
            self.db.commit()
            self.db.refresh(transaction)
            
            self.logger.info(f"Transaction created successfully: {transaction.id}")
            return transaction
        except Exception as e:
            self.logger.error(f"Error creating transaction: {str(e)}")
            self.db.rollback()
            raise
            
    def get_by_ticker(self, ticker: str, limit: int = 10) -> List[TransactionEntity]:
        """
        Получает список транзакций по тикеру
        
        Args:
            ticker: Тикер инструмента
            limit: Максимальное количество транзакций
        """
        self.logger.debug(f"Fetching transactions for ticker: {ticker}, limit={limit}")
        
        try:
            transactions = (
                self.db.query(TransactionEntity)
                .filter(TransactionEntity.ticker == ticker)
                .order_by(TransactionEntity.timestamp.desc())
                .limit(limit)
                .all()
            )
            
            self.logger.debug(f"Found {len(transactions)} transactions for ticker {ticker}")
            return transactions
        except Exception as e:
            self.logger.error(f"Error fetching transactions for ticker {ticker}: {str(e)}")
            raise
            
    def get_by_id(self, transaction_id: UUID) -> Optional[TransactionEntity]:
        """
        Получает транзакцию по ID
        
        Args:
            transaction_id: Идентификатор транзакции
        """
        self.logger.debug(f"Fetching transaction by ID: {transaction_id}")
        
        try:
            transaction = self.db.query(TransactionEntity).filter(
                TransactionEntity.id == transaction_id
            ).first()
            
            if transaction:
                self.logger.debug(f"Found transaction: {transaction_id}")
            else:
                self.logger.debug(f"Transaction not found: {transaction_id}")
                
            return transaction
        except Exception as e:
            self.logger.error(f"Error fetching transaction {transaction_id}: {str(e)}")
            raise
        
    def get_by_order(self, order_id: UUID) -> List[TransactionEntity]:
        """
        Получает список транзакций по ID ордера
        
        Args:
            order_id: Идентификатор ордера
        """
        self.logger.debug(f"Fetching transactions for order: {order_id}")
        
        try:
            transactions = self.db.query(TransactionEntity).filter(
                (TransactionEntity.buyer_order_id == order_id) | 
                (TransactionEntity.seller_order_id == order_id)
            ).order_by(TransactionEntity.timestamp.desc()).all()
            
            self.logger.debug(f"Found {len(transactions)} transactions for order {order_id}")
            return transactions
        except Exception as e:
            self.logger.error(f"Error fetching transactions for order {order_id}: {str(e)}")
            raise
        
    def to_model(self, entity: TransactionEntity) -> Transaction:
        """
        Преобразует сущность в модель транзакции
        """
        return Transaction(
            id=str(entity.id),
            ticker=entity.ticker,
            amount=entity.amount,
            price=entity.price,
            buyer_order_id=str(entity.buyer_order_id),
            seller_order_id=str(entity.seller_order_id),
            timestamp=entity.timestamp
        )
