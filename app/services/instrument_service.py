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

    async def add_instrument(self, instrument: Instrument) -> Ok:
        """Добавляет новый инструмент"""
        self.logger.info(f"Adding new instrument: {instrument.ticker} ({instrument.name})")
        
        # Проверка на существование инструмента с таким тикером
        existing = self.repository.get_by_ticker(instrument.ticker)
        if existing:
            self.logger.warning(f"Instrument with ticker {instrument.ticker} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instrument with ticker {instrument.ticker} already exists",
            )

        try:
            self.repository.create(instrument.name, instrument.ticker)
            self.logger.info(f"Successfully created instrument: {instrument.ticker}")
            return Ok()
        except Exception as e:
            self.logger.error(f"Failed to create instrument {instrument.ticker}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create instrument",
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
