from typing import List, Union
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging import setup_logger
from app.entities.order import OrderEntity
from app.models.base import Direction, OrderStatus, L2OrderBook, Level, Transaction
from app.models.order import LimitOrderBody, MarketOrderBody, LimitOrder, MarketOrder
from app.repositories.balance_repository import BalanceRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.transaction_repository import TransactionRepository


class ExchangeService:
    def __init__(self, db: Session):
        self.db = db
        self.logger = setup_logger("app.services.exchange")
        self.order_repo = OrderRepository(db)
        self.balance_repo = BalanceRepository(db)
        self.transaction_repo = TransactionRepository(db)
        self.instrument_repo = InstrumentRepository(db)

    async def get_orderbook(self, ticker: str, limit: int = 10) -> L2OrderBook:
        # Получаем все активные ордера для данного инструмента
        active_orders = self.order_repo.get_active_by_ticker(ticker)

        # Разделяем на покупки (bid) и продажи (ask)
        bids = [order for order in active_orders if order.direction == Direction.BUY and order.type == 'limit']
        asks = [order for order in active_orders if order.direction == Direction.SELL and order.type == 'limit']

        # Сортируем bids по возрастанию цены (лучшая цена покупки - самая высокая)
        bids.sort(key=lambda x: x.price, reverse=True)
        # Сортируем asks по убыванию цены (лучшая цена продажи - самая низкая)
        asks.sort(key=lambda x: x.price)

        # Группируем по ценовым уровням и суммируем количество
        bid_levels = {}
        for bid in bids:
            if bid.price in bid_levels:
                bid_levels[bid.price] += bid.qty - bid.filled
            else:
                bid_levels[bid.price] = bid.qty - bid.filled

        ask_levels = {}
        for ask in asks:
            if ask.price in ask_levels:
                ask_levels[ask.price] += ask.qty - ask.filled
            else:
                ask_levels[ask.price] = ask.qty - ask.filled

        # Формируем ответ
        bid_result = [Level(price=price, qty=qty) for price, qty in bid_levels.items()]
        ask_result = [Level(price=price, qty=qty) for price, qty in ask_levels.items()]

        # Ограничиваем количество уровней
        bid_result = bid_result[:limit]
        ask_result = ask_result[:limit]

        return L2OrderBook(bid_levels=bid_result, ask_levels=ask_result)

    async def get_transaction_history(self, ticker: str, limit: int = 10) -> List[Transaction]:
        transactions = self.transaction_repo.get_by_ticker(ticker, limit)
        return [self.transaction_repo.to_model(t) for t in transactions]

    async def create_limit_order(self, user_id: UUID, body: LimitOrderBody) -> str:
        # Проверяем существование инструмента
        instrument = self.instrument_repo.get_by_ticker(body.ticker)
        if not instrument:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument {body.ticker} not found"
            )

        # Проверяем достаточно ли средств у пользователя
        if body.direction == Direction.BUY:
            # Для покупки нужны рубли
            balance = self.balance_repo.get_by_user_and_ticker(user_id, "RUB")
            required_amount = body.price * body.qty

            if not balance or (balance.amount - balance.locked_amount) < required_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient RUB balance for order"
                )

            # Блокируем средства вместо их списания
            balance_locked = self.balance_repo.lock_balance(user_id, "RUB", required_amount)
            if balance_locked is None:
                available = self.balance_repo.get_by_user_and_ticker(user_id, "RUB")
                available_amount = (available.amount - available.locked_amount) if available else 0
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Недостаточно доступных средств RUB для блокировки (доступно {available_amount}, требуется {required_amount})"
                )
        else:  # Direction.SELL
            # Для продажи нужны акции
            balance = self.balance_repo.get_by_user_and_ticker(user_id, body.ticker)

            if not balance or balance.amount < body.qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient {body.ticker} balance for order"
                )

            # Блокируем акции вместо их списания
            balance_locked = self.balance_repo.lock_balance(user_id, body.ticker, body.qty)
            if balance_locked is None:
                available = self.balance_repo.get_by_user_and_ticker(user_id, body.ticker)
                available_amount = (available.amount - available.locked_amount) if available else 0
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Недостаточно доступных средств {body.ticker} для блокировки (доступно {available_amount}, требуется {body.qty})"
                )

        # Создаем ордер
        order = self.order_repo.create_limit_order(user_id, body)

        # Выполняем матчинг ордеров
        await self._match_orders(order.id)

        return str(order.id)

    async def create_market_order(self, user_id: UUID, body: MarketOrderBody) -> str:
        # Проверяем существование инструмента
        instrument = self.instrument_repo.get_by_ticker(body.ticker)
        if not instrument:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument {body.ticker} not found"
            )

        # Получаем стакан для проверки ликвидности
        orderbook = await self.get_orderbook(body.ticker)

        if body.direction == Direction.BUY:
            # Для покупки нужны ask ордера
            if not orderbook.ask_levels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No sellers available for market buy"
                )

            # Рассчитываем необходимую сумму для покупки
            required_amount = 0
            remaining_qty = body.qty

            for level in orderbook.ask_levels:
                if remaining_qty <= 0:
                    break

                level_qty = min(remaining_qty, level.qty)
                required_amount += level_qty * level.price
                remaining_qty -= level_qty

            if remaining_qty > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Not enough liquidity in the order book"
                )

            # Проверяем баланс
            balance = self.balance_repo.get_by_user_and_ticker(user_id, "RUB")
            if not balance or balance.amount < required_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient RUB balance for market order"
                )

            # Блокируем средства вместо их списания
            balance_locked = self.balance_repo.lock_balance(user_id, "RUB", required_amount)
            if balance_locked is None:
                available = self.balance_repo.get_by_user_and_ticker(user_id, "RUB")
                available_amount = (available.amount - available.locked_amount) if available else 0
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Недостаточно доступных средств RUB для блокировки (доступно {available_amount}, требуется {required_amount})"
                )
        else:  # Direction.SELL
            # Для продажи нужны bid ордера
            if not orderbook.bid_levels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No buyers available for market sell"
                )

            # Проверяем баланс акций
            balance = self.balance_repo.get_by_user_and_ticker(user_id, body.ticker)
            if not balance or balance.amount < body.qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient {body.ticker} balance for market order"
                )

            # Проверяем, хватит ли ликвидности для продажи
            available_qty = sum(level.qty for level in orderbook.bid_levels)
            if available_qty < body.qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Not enough liquidity in the order book"
                )

            # Блокируем акции вместо их списания
            balance_locked = self.balance_repo.lock_balance(user_id, body.ticker, body.qty)
            if balance_locked is None:
                available = self.balance_repo.get_by_user_and_ticker(user_id, body.ticker)
                available_amount = (available.amount - available.locked_amount) if available else 0
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Недостаточно доступных средств {body.ticker} для блокировки (доступно {available_amount}, требуется {body.qty})"
                )

        # Создаем маркет-ордер
        order = self.order_repo.create_market_order(user_id, body)

        # Выполняем матчинг ордеров и обработку транзакций со списанием заблокированных средств
        # Обратите внимание, в методе _match_orders нужно добавить вызовы unlock_and_subtract_balance
        # для списания заблокированных средств при исполнении ордера
        await self._match_orders(order.id)

        return str(order.id)

    async def get_order(self, order_id: UUID) -> Union[LimitOrder, MarketOrder]:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with id {order_id} not found"
            )

        return self.order_repo.to_model(order)

    async def cancel_order(self, user_id: UUID, order_id: UUID) -> bool:
        order = self.order_repo.get_by_id(order_id)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with id {order_id} not found"
            )

        if str(order.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own orders"
            )

        if order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order with status {order.status}"
            )

        # Разблокируем средства обратно на баланс пользователя
        if order.direction == Direction.BUY:
            # Разблокируем неиспользованные средства
            remaining_value = (order.qty - order.filled) * order.price
            if remaining_value > 0:
                balance_result = self.balance_repo.unlock_balance(user_id, "RUB", remaining_value)
                if balance_result is None:
                    self.logger.error(f"Ошибка при разблокировке средств: user_id={user_id}, ticker=RUB, amount={remaining_value}")
        else:  # Direction.SELL
            # Разблокируем неиспользованные акции
            remaining_qty = order.qty - order.filled
            if remaining_qty > 0:
                balance_result = self.balance_repo.unlock_balance(user_id, order.ticker, remaining_qty)
                if balance_result is None:
                    self.logger.error(f"Ошибка при разблокировке средств: user_id={user_id}, ticker={order.ticker}, amount={remaining_qty}")

        # Отменяем ордер
        result = self.order_repo.cancel_order(order_id)

        return result

    async def get_user_orders(self, user_id: UUID) -> List[Union[LimitOrder, MarketOrder]]:
        orders = self.order_repo.get_all_by_user(user_id)
        return [self.order_repo.to_model(order) for order in orders]

    async def _match_orders(self, order_id: UUID) -> None:
        """Внутренний метод для сопоставления ордеров и выполнения сделок"""
        order = self.order_repo.get_by_id(order_id)

        if not order:
            return

        # Если ордер уже исполнен или отменен, ничего не делаем
        if order.status in [OrderStatus.EXECUTED, OrderStatus.CANCELLED]:
            return

        # Находим встречные ордера
        is_buy = order.direction == Direction.BUY
        counter_direction = Direction.SELL if is_buy else Direction.BUY

        # Получаем все активные ордера с противоположным направлением
        active_orders = self.db.query(OrderEntity).filter(
            OrderEntity.ticker == order.ticker,
            OrderEntity.direction == counter_direction,
            OrderEntity.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
            OrderEntity.id != order.id
        )

        # Для лимитных ордеров учитываем цену
        if order.type == 'limit':
            if is_buy:
                # Для покупки берем только ордера с ценой ниже или равной нашей цене
                active_orders = active_orders.filter(OrderEntity.price <= order.price)
                # Сортируем по цене (сначала самые дешевые)
                active_orders = active_orders.order_by(OrderEntity.price.asc(), OrderEntity.created_at)
            else:
                # Для продажи берем только ордера с ценой выше или равной нашей цене
                active_orders = active_orders.filter(OrderEntity.price >= order.price)
                # Сортируем по цене (сначала самые дорогие)
                active_orders = active_orders.order_by(OrderEntity.price.desc(), OrderEntity.created_at)
        else:  # market order
            if is_buy:
                # Для покупки берем самые дешевые ордера сначала
                active_orders = active_orders.order_by(OrderEntity.price.asc(), OrderEntity.created_at)
            else:
                # Для продажи берем самые дорогие ордера сначала
                active_orders = active_orders.order_by(OrderEntity.price.desc(), OrderEntity.created_at)

        # Получаем список ордеров для матчинга
        matching_orders = active_orders.all()

        # Если нет встречных ордеров, выходим
        if not matching_orders:
            return

        # Выполняем сделки
        remaining_qty = order.qty - order.filled

        for matching_order in matching_orders:
            if remaining_qty <= 0:
                break

            # Определяем цену сделки
            if order.type == 'market':
                # Для маркет-ордеров берем цену из встречного ордера
                execution_price = matching_order.price
            else:
                # Для лимитных ордеров берем цену того ордера, который был первым
                if order.created_at < matching_order.created_at:
                    execution_price = order.price
                else:
                    execution_price = matching_order.price

            # Определяем количество для сделки
            matching_remaining = matching_order.qty - matching_order.filled
            execution_qty = min(remaining_qty, matching_remaining)

            # Обновляем статус обоих ордеров
            # Обновляем основной ордер
            order.filled += execution_qty
            if order.filled == order.qty:
                order.status = OrderStatus.EXECUTED
            else:
                order.status = OrderStatus.PARTIALLY_EXECUTED

            # Обновляем встречный ордер
            matching_order.filled += execution_qty
            if matching_order.filled == matching_order.qty:
                matching_order.status = OrderStatus.EXECUTED
            else:
                matching_order.status = OrderStatus.PARTIALLY_EXECUTED

            # Обновляем балансы пользователей
            if is_buy:
                # Разблокируем и списываем средства покупателя (RUB)
                balance_result = self.balance_repo.unlock_and_subtract_balance(order.user_id, "RUB", execution_qty * execution_price)
                if balance_result is None:
                    self.logger.error(f"Ошибка при списании средств покупателя: user_id={order.user_id}, amount={execution_qty * execution_price}")

                # Покупатель получает акции
                self.balance_repo.update_balance(order.user_id, order.ticker, execution_qty)

                # Разблокируем и списываем акции продавца
                balance_result = self.balance_repo.unlock_and_subtract_balance(matching_order.user_id, order.ticker, execution_qty)
                if balance_result is None:
                    self.logger.error(f"Ошибка при списании акций продавца: user_id={matching_order.user_id}, ticker={order.ticker}, amount={execution_qty}")

                # Продавец получает деньги
                self.balance_repo.update_balance(matching_order.user_id, "RUB", execution_qty * execution_price)
            else:
                # Разблокируем и списываем акции продавца (order.user_id)
                balance_result = self.balance_repo.unlock_and_subtract_balance(order.user_id, order.ticker, execution_qty)
                if balance_result is None:
                    self.logger.error(f"Ошибка при списании акций продавца: user_id={order.user_id}, ticker={order.ticker}, amount={execution_qty}")

                # Продавец получает деньги
                self.balance_repo.update_balance(order.user_id, "RUB", execution_qty * execution_price)

                # Разблокируем и списываем средства покупателя
                balance_result = self.balance_repo.unlock_and_subtract_balance(matching_order.user_id, "RUB", execution_qty * execution_price)
                if balance_result is None:
                    self.logger.error(f"Ошибка при списании средств покупателя: user_id={matching_order.user_id}, amount={execution_qty * execution_price}")

                # Покупатель получает акции
                self.balance_repo.update_balance(matching_order.user_id, order.ticker, execution_qty)

            buyer_order_id = order.id if is_buy else matching_order.id
            seller_order_id = matching_order.id if is_buy else order.id

            # Создаем запись о транзакции
            self.logger.info(f"Creating transaction: ticker={order.ticker}, amount={execution_qty}, price={execution_price}")
            try:
                self.transaction_repo.create(
                    ticker=order.ticker,
                    amount=execution_qty,
                    price=execution_price,
                    buyer_order_id=buyer_order_id,
                    seller_order_id=seller_order_id
                )
                self.logger.info(f"Transaction created successfully for order {order.id} with {matching_order.id}")
            except Exception as e:
                self.logger.error(f"Error creating transaction: {e}")
                raise

            # Обновляем остаток для следующей итерации
            remaining_qty -= execution_qty

        # Сохраняем изменения в базе данных
        self.db.commit()
