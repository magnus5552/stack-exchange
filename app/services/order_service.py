from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.order import OrderEntity, LimitOrderEntity, MarketOrderEntity
from app.core.logging import setup_logger


class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.logger = setup_logger("app.services.order")

    def get_by_id(self, order_id: UUID) -> Optional[OrderEntity]:
        """
        Получает ордер по его идентификатору
        
        Args:
            order_id: Идентификатор ордера
            
        Returns:
            Сущность ордера или None, если ордер не найден
        """
        self.logger.debug(f"Получение ордера по ID: {order_id}")
        
        try:
            order = self.db.query(OrderEntity).filter(OrderEntity.id == order_id).first()
            
            if order:
                self.logger.debug(f"Ордер найден: {order_id}")
            else:
                self.logger.debug(f"Ордер не найден: {order_id}")
                
            return order
        except Exception as e:
            self.logger.error(f"Ошибка при получении ордера {order_id}: {str(e)}")
            raise
            
    def get_user_orders(self, user_id: UUID) -> List[OrderEntity]:
        """
        Получает все ордера пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список ордеров
        """
        self.logger.debug(f"Получение ордеров пользователя: {user_id}")
        
        try:
            orders = self.db.query(OrderEntity).filter(OrderEntity.user_id == user_id).all()
            self.logger.debug(f"Найдено {len(orders)} ордеров для пользователя {user_id}")
            return orders
        except Exception as e:
            self.logger.error(f"Ошибка при получении ордеров пользователя {user_id}: {str(e)}")
            raise
