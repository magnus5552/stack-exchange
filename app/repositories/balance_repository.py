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

    def lock_balance(self, user_id: UUID, ticker: str, amount: int) -> BalanceEntity:
        """
        Блокирует средства на балансе пользователя для ордера.
        Проверяет наличие доступных (незаблокированных) средств.
        """
        self.logger.debug(f"Блокировка средств: user_id={user_id}, ticker={ticker}, amount={amount}")
        
        # Получаем баланс с блокировкой строки
        balance = (
            self.db.query(BalanceEntity)
            .filter(BalanceEntity.user_id == user_id, BalanceEntity.ticker == ticker)
            .with_for_update()
            .first()
        )
        
        if not balance:
            # Создаем новый баланс, если его нет
            balance = BalanceEntity(
                user_id=user_id,
                ticker=ticker,
                amount=0,
                locked_amount=0
            )
            self.db.add(balance)
            self.db.flush()
        
        # Проверяем, хватает ли доступных средств для блокировки
        available_amount = balance.amount - balance.locked_amount
        if available_amount < amount:
            self.logger.warning(f"Недостаточно доступных средств для блокировки: {ticker}, доступно={available_amount}, требуется={amount}")
            self.db.rollback()
            return None
        
        # Блокируем средства (увеличиваем locked_amount)
        balance.locked_amount += amount
        
        self.db.commit()
        self.logger.debug(f"Средства заблокированы: user_id={user_id}, ticker={ticker}, locked_amount={balance.locked_amount}")
        return balance
    
    def unlock_balance(self, user_id: UUID, ticker: str, amount: int) -> BalanceEntity:
        """
        Разблокирует средства на балансе пользователя (без их списания)
        """
        self.logger.debug(f"Разблокировка средств: user_id={user_id}, ticker={ticker}, amount={amount}")
        
        # Получаем баланс с блокировкой строки
        balance = (
            self.db.query(BalanceEntity)
            .filter(BalanceEntity.user_id == user_id, BalanceEntity.ticker == ticker)
            .with_for_update()
            .first()
        )
        
        if not balance or balance.locked_amount < amount:
            self.logger.warning(f"Недостаточно заблокированных средств для разблокировки: {ticker}, заблокировано={balance.locked_amount if balance else 0}, требуется={amount}")
            self.db.rollback()
            return None
        
        # Разблокируем средства (уменьшаем locked_amount)
        balance.locked_amount -= amount
        
        self.db.commit()
        return balance
    
    def unlock_and_subtract_balance(self, user_id: UUID, ticker: str, amount: int) -> BalanceEntity:
        """
        Разблокирует и одновременно списывает средства с баланса пользователя
        """
        self.logger.debug(f"Разблокировка и списание средств: user_id={user_id}, ticker={ticker}, amount={amount}")
        
        # Получаем баланс с блокировкой строки
        balance = (
            self.db.query(BalanceEntity)
            .filter(BalanceEntity.user_id == user_id, BalanceEntity.ticker == ticker)
            .with_for_update()
            .first()
        )
        
        if not balance or balance.locked_amount < amount or balance.amount < amount:
            self.logger.warning(f"Недостаточно средств для разблокировки и списания: {ticker}, " +
                f"заблокировано={balance.locked_amount if balance else 0}, баланс={balance.amount if balance else 0}, требуется={amount}")
            self.db.rollback()
            return None
        
        # Разблокируем и списываем средства
        balance.locked_amount -= amount
        balance.amount -= amount
        
        self.db.commit()
        return balance
    
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

    # Оставляем для обратной совместимости
    def withdraw_locked_amount(self, user_id: UUID, ticker: str, amount: int) -> BalanceEntity:
        """
        Списывает указанную сумму средств из заблокированных и с баланса.
        Используется при исполнении ордера.
        
        @deprecated Используйте unlock_and_subtract_balance вместо этого метода
        """
        return self.unlock_and_subtract_balance(user_id, ticker, amount)
        
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
