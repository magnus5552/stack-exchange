from typing import List, Optional
from sqlalchemy.orm import Session
from app.entities.instrument import InstrumentEntity
from app.entities.transaction import TransactionEntity
from app.models.instrument import Instrument
from app.core.logging import setup_logger


class InstrumentRepository:
    def __init__(self, db: Session):
        self.db = db
        self.logger = setup_logger("app.repositories.instrument")
        self._model = InstrumentEntity  # Для совместимости с init_db

    def create(self, name: str, ticker: str) -> InstrumentEntity:
        """
        Создает новый инструмент в БД или активирует существующий неактивный

        Если инструмент существует, но неактивен, он будет активирован и
        его имя будет обновлено.
        """
        self.logger.info(f"Creating/activating instrument: ticker={ticker}, name={name}")

        try:
            # Проверяем существование инструмента (включая неактивные)
            existing_instrument = self.get_by_ticker(ticker, only_active=False)

            if existing_instrument:
                if existing_instrument.is_active:
                    self.logger.warning(f"Instrument {ticker} already exists and is active")
                    return existing_instrument
                else:
                    # Реактивируем инструмент
                    self.logger.info(f"Reactivating existing instrument: {ticker}")
                    existing_instrument.is_active = True
                    existing_instrument.name = name  # Обновляем имя
                    self.db.commit()
                    self.db.refresh(existing_instrument)
                    self.logger.info(f"Instrument {ticker} reactivated successfully")
                    return existing_instrument
            else:
                # Создаем новый инструмент
                db_instrument = InstrumentEntity(name=name, ticker=ticker)
                self.db.add(db_instrument)
                self.db.commit()
                self.db.refresh(db_instrument)

                self.logger.info(f"Instrument {ticker} created successfully")
                return db_instrument
        except Exception as e:
            self.logger.error(f"Error creating/activating instrument {ticker}: {str(e)}")
        self.db.rollback()
        raise

    def get_by_ticker(self, ticker: str, only_active: bool = True) -> Optional[InstrumentEntity]:
        """
        Получает инструмент по тикеру

        Args:
            ticker: Тикер инструмента
            only_active: Если True, возвращает только активные инструменты
        """
        self.logger.debug(f"Fetching instrument by ticker: {ticker}, only_active={only_active}")

        try:
            query = self.db.query(InstrumentEntity).filter(InstrumentEntity.ticker == ticker)

            if only_active:
                query = query.filter(InstrumentEntity.is_active == True)

            instrument = query.first()

            if instrument:
                status = "active" if instrument.is_active else "inactive"
                self.logger.debug(f"Found {status} instrument: {ticker}")
            else:
                self.logger.debug(f"Instrument not found: {ticker}")

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
        """Удаляет (деактивирует) инструмент по тикеру и все связанные транзакции"""
        self.logger.info(f"Deactivating instrument: {ticker}")
        
        try:
            instrument = self.get_by_ticker(ticker)
            if not instrument:
                self.logger.warning(f"Delete failed: Active instrument {ticker} not found")
                return False
    
            # Удаляем все транзакции, связанные с этим инструментом
            self.logger.info(f"Deleting all transactions for ticker: {ticker}")
            transactions = self.db.query(TransactionEntity).filter(
                TransactionEntity.ticker == ticker
            ).all()
            
            if transactions:
                self.logger.info(f"Found {len(transactions)} transactions to delete for {ticker}")
                for transaction in transactions:
                    self.db.delete(transaction)
                self.logger.info(f"All transactions for {ticker} have been deleted")
            else:
                self.logger.info(f"No transactions found for ticker {ticker}")
    
            # Софт-удаление (деактивация) инструмента
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
