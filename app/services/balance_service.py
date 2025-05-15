from typing import Dict
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.base import Ok
from app.repositories.balance_repository import BalanceRepository
from app.repositories.user_repository import UserRepository
from app.repositories.instrument_repository import InstrumentRepository


class BalanceService:
    def __init__(self, db: Session):
        self.db = db
        self.balance_repo = BalanceRepository(db)
        self.user_repo = UserRepository(db)
        self.instrument_repo = InstrumentRepository(db)

    async def get_user_balances(self, user_id: UUID) -> Dict[str, int]:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

        balances = self.balance_repo.get_all_by_user(user_id)

        return {balance.ticker: balance.amount for balance in balances}

    async def deposit(self, user_id: UUID, ticker: str, amount: int) -> Ok:
        """
        Пополняет баланс пользователя

        Args:
            user_id: Идентификатор пользователя
            ticker: Тикер инструмента
            amount: Сумма пополнения (должна быть положительной)

        Returns:
            Ok: Результат успешной операции

        Raises:
            HTTPException: Если пользователь не найден, инструмент не найден или сумма неверна
        """
        # Проверяем существование пользователя
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active user with id {user_id} not found",
            )

        # Проверяем существование инструмента, кроме рубля (особый случай)
        if ticker != "RUB":
            instrument = self.instrument_repo.get_by_ticker(ticker)
            if not instrument:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Instrument with ticker {ticker} not found",
                )

        # Проверяем корректность суммы
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be positive",
            )

        # Обновляем баланс
        self.balance_repo.update_balance(user_id, ticker, amount)

        return Ok()

    async def withdraw(self, user_id: UUID, ticker: str, amount: int) -> Ok:
        """
        Списывает средства с баланса пользователя

        Args:
            user_id: Идентификатор пользователя
            ticker: Тикер инструмента
            amount: Сумма списания (должна быть положительной)

        Returns:
            Ok: Результат успешной операции

        Raises:
            HTTPException: Если пользователь не найден, инструмент не найден,
                          сумма неверна или недостаточно средств
        """
        # Проверяем существование пользователя
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active user with id {user_id} not found",
            )

        # Проверяем существование инструмента, кроме рубля (особый случай)
        if ticker != "RUB":
            instrument = self.instrument_repo.get_by_ticker(ticker)
            if not instrument:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Instrument with ticker {ticker} not found",
                )

        # Проверяем корректность суммы
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be positive",
            )

        # Проверяем достаточность средств
        balance = self.balance_repo.get_by_user_and_ticker(user_id, ticker)
        if not balance or balance.amount < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient {ticker} balance",
            )

        # Списываем средства
        self.balance_repo.update_balance(user_id, ticker, -amount)

        return Ok()