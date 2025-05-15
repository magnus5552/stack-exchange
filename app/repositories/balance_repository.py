from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.balance import BalanceEntity
from app.tasks.balance_tasks import update_balance_async
from app.core.logging import setup_logger


class BalanceRepository:
    def __init__(self, db: Session):
        self.db = db
        self.logger = setup_logger("app.repositories.balance")

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
        """
        Обновляет баланс, используя блокировку FOR UPDATE для предотвращения race condition
        """
        self.logger.debug(f"Обновление баланса: user_id={user_id}, ticker={ticker}, amount={amount}")
        
        # Используем блокировку строки для атомарной операции
        balance = (
            self.db.query(BalanceEntity)
            .filter(BalanceEntity.user_id == user_id, BalanceEntity.ticker == ticker)
            .with_for_update()
            .first()
        )

        if balance:
            balance.amount += amount
        else:
            balance = BalanceEntity(user_id=user_id, ticker=ticker, amount=amount)
            self.db.add(balance)

        self.db.commit()
        self.db.refresh(balance)
        self.logger.debug(f"Баланс обновлен: user_id={user_id}, ticker={ticker}, new_amount={balance.amount}")
        return balance
        
    def update_balance_async(self, user_id: UUID, ticker: str, amount: int) -> None:
        """
        Запускает асинхронную задачу для обновления баланса
        """
        self.logger.debug(f"Запуск асинхронного обновления баланса: user_id={user_id}, ticker={ticker}, amount={amount}")
        try:
            # Если Redis недоступен, выполняем обновление синхронно
            try:
                from app.tasks.balance_tasks import update_balance_async
                update_balance_async.delay(str(user_id), ticker, amount)
                self.logger.debug(f"Задача поставлена в очередь: user_id={user_id}, ticker={ticker}")
            except Exception as e:
                self.logger.error(f"Ошибка при запуске асинхронной задачи: {str(e)}. Выполняю синхронное обновление.")
                self.update_balance(user_id, ticker, amount)
        except Exception as e:
            self.logger.error(f"Критическая ошибка при обновлении баланса: {str(e)}")
            # В случае критической ошибки, запись в лог и возможно уведомление
