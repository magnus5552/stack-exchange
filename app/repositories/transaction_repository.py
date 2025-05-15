from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.logging import setup_logger
from app.entities.transaction import TransactionEntity
from app.models.base import Transaction
from app.repositories.balance_repository import BalanceRepository


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db
        self.logger = setup_logger("app.repositories.transaction")
        self.balance_repository = BalanceRepository(db)
        
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
            
            # Запускаем асинхронное обновление балансов для улучшения производительности
            # Вместо прямого обновления используем асинхронную задачу
            from app.services.order_service import OrderService
            order_service = OrderService(self.db)
            
            # Получаем информацию о ордерах
            try:
                buyer_order = order_service.get_by_id(buyer_order_id)
                seller_order = order_service.get_by_id(seller_order_id)
            except Exception as e:
                self.logger.error(f"Ошибка при получении ордеров: {str(e)}")
                # Продолжаем выполнение, даже если не можем получить ордеры
                buyer_order = None
                seller_order = None
            
            # Если у нас есть оба ордера, выполняем асинхронное обновление балансов
            if buyer_order and seller_order:
                try:
                    # Асинхронно обновляем баланс покупателя (добавляем актив)
                    self.balance_repository.update_balance_async(
                        buyer_order.user_id, ticker, amount
                    )
                    # Асинхронно обновляем баланс продавца (вычитаем актив)
                    self.balance_repository.update_balance_async(
                        seller_order.user_id, ticker, -amount
                    )
                    
                    # Асинхронно обновляем баланс денег
                    total_price = amount * price
                    self.balance_repository.update_balance_async(
                        buyer_order.user_id, "RUB", -total_price
                    )
                    self.balance_repository.update_balance_async(
                        seller_order.user_id, "RUB", total_price
                    )
                    
                    self.logger.info(f"Запущены асинхронные задачи обновления балансов для транзакции {transaction.id}")
                except Exception as e:
                    self.logger.error(f"Ошибка при обновлении балансов: {str(e)}. Транзакция создана, но балансы могут быть не обновлены.")
            else:
                self.logger.warning(
                    f"Невозможно обновить балансы асинхронно: один или оба ордера не найдены. "
                    f"buyer_order_id={buyer_order_id}, seller_order_id={seller_order_id}"
                )
                # В этом случае можно использовать другую стратегию обновления балансов,
                # например, через событийную модель или другой сервис
            
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
