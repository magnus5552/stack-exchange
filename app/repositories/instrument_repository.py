from typing import List, Optional
from sqlalchemy.orm import Session
from app.entities.instrument import InstrumentEntity
from app.models.instrument import Instrument
from app.core.logging import setup_logger


class InstrumentRepository:
    def __init__(self, db: Session):
        self.db = db
        self.logger = setup_logger("app.repositories.instrument")
        self._model = InstrumentEntity  # Для совместимости с init_db

    def create(self, name: str, ticker: str) -> InstrumentEntity:
        """Создает новый инструмент в БД"""
        self.logger.info(f"Creating new instrument: ticker={ticker}, name={name}")
        
        try:
            db_instrument = InstrumentEntity(name=name, ticker=ticker)
            self.db.add(db_instrument)
            self.db.commit()
            self.db.refresh(db_instrument)
            
            self.logger.info(f"Instrument {ticker} created successfully")
            return db_instrument
        except Exception as e:
            self.logger.error(f"Error creating instrument {ticker}: {str(e)}")
            self.db.rollback()
            raise

    def get_by_ticker(self, ticker: str) -> Optional[InstrumentEntity]:
        """Получает инструмент по тикеру"""
        self.logger.debug(f"Fetching instrument by ticker: {ticker}")
        
        try:
            instrument = (
                self.db.query(InstrumentEntity)
                .filter(
                    InstrumentEntity.ticker == ticker, 
                    InstrumentEntity.is_active == True
                )
                .first()
            )
            
            if instrument:
                self.logger.debug(f"Found active instrument: {ticker}")
            else:
                self.logger.debug(f"Active instrument not found: {ticker}")
                
            return instrument
        except Exception as e:
            self.logger.error(f"Error fetching instrument {ticker}: {str(e)}")
            raise

    def get_all_active(self) -> List[InstrumentEntity]:
        """Получает все активные инструменты"""
        self.logger.debug("Fetching all active instruments")
        
        try:
            instruments = (
                self.db.query(InstrumentEntity)
                .filter(InstrumentEntity.is_active == True)
                .all()
            )
            
            self.logger.debug(f"Found {len(instruments)} active instruments")
            return instruments
        except Exception as e:
            self.logger.error(f"Error fetching active instruments: {str(e)}")
            raise

    def delete(self, ticker: str) -> bool:
        """Удаляет (деактивирует) инструмент по тикеру"""
        self.logger.info(f"Deactivating instrument: {ticker}")
        
        try:
            instrument = self.get_by_ticker(ticker)
            if not instrument:
                self.logger.warning(f"Delete failed: Active instrument {ticker} not found")
                return False

            # Софт-удаление (деактивация)
            instrument.is_active = False
            self.db.commit()
            
            self.logger.info(f"Instrument {ticker} deactivated successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error deactivating instrument {ticker}: {str(e)}")
            self.db.rollback()
            raise

    def to_model(self, entity: InstrumentEntity) -> Instrument:
        """Преобразует сущность в модель инструмента"""
        self.logger.debug(f"Converting instrument entity to model: ticker={entity.ticker}")
        return Instrument(
            name=entity.name, 
            ticker=entity.ticker, 
            active=entity.is_active
        )
