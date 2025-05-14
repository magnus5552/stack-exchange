from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.instrument import Instrument
from app.models.base import Ok
from app.repositories.instrument_repository import InstrumentRepository
from app.core.logging import setup_logger


class InstrumentService:
    def __init__(self, db: Session):
        self.repository = InstrumentRepository(db)
        self.logger = setup_logger("app.services.instrument")

    async def get_all_instruments(self) -> List[Instrument]:
        """Получает список всех активных инструментов"""
        self.logger.info("Getting all active instruments")
        instruments = self.repository.get_all_active()
        count = len(instruments)
        self.logger.debug(f"Found {count} active instruments")
        return [self.repository.to_model(i) for i in instruments]

    async def get_instrument(self, ticker: str, include_inactive: bool = False) -> Instrument:
        """
        Получает инструмент по тикеру
        
        Args:
            ticker: Тикер инструмента
            include_inactive: Если True, ищет также среди неактивных инструментов
            
        Returns:
            Instrument: Модель инструмента
            
        Raises:
            HTTPException: Если инструмент не найден
        """
        self.logger.info(f"Getting instrument: {ticker}, include_inactive={include_inactive}")
        
        entity = self.repository.get_by_ticker(ticker, only_active=not include_inactive)
        if not entity:
            self.logger.warning(f"Instrument with ticker {ticker} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument with ticker {ticker} not found",
            )
            
        return self.repository.to_model(entity)

    async def add_instrument(self, instrument: Instrument) -> Ok:
            """
            Добавляет новый инструмент или активирует существующий неактивный
            
            Если инструмент уже существует и активен, возвращается ошибка.
            Если инструмент существует, но неактивен (был удален), он будет активирован.
            """
            self.logger.info(f"Adding/activating instrument: {instrument.ticker} ({instrument.name})")
            
            # Проверка на существование активного инструмента с таким тикером
            existing = self.repository.get_by_ticker(instrument.ticker, only_active=True)
            if existing:
                self.logger.warning(f"Active instrument with ticker {instrument.ticker} already exists")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Instrument with ticker {instrument.ticker} already exists",
                )
    
            try:
                # Метод create теперь автоматически активирует существующий неактивный инструмент
                self.repository.create(instrument.name, instrument.ticker)
                self.logger.info(f"Successfully created/activated instrument: {instrument.ticker}")
                return Ok()
            except Exception as e:
                self.logger.error(f"Failed to create/activate instrument {instrument.ticker}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create/activate instrument: {str(e)}",
            )

    async def delete_instrument(self, ticker: str) -> Ok:
        """Удаляет инструмент"""
        self.logger.info(f"Deleting instrument: {ticker}")
        
        # Проверка на существование инструмента
        existing = self.repository.get_by_ticker(ticker)
        if not existing:
            self.logger.warning(f"Instrument with ticker {ticker} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument with ticker {ticker} not found",
            )

        try:
            success = self.repository.delete(ticker)
            if not success:
                self.logger.error(f"Failed to delete instrument {ticker}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete instrument",
                )
            
            self.logger.info(f"Successfully deleted instrument: {ticker}")
            return Ok()
        except Exception as e:
            self.logger.error(f"Error deleting instrument {ticker}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete instrument: {str(e)}",
            )
