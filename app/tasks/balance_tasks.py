from uuid import UUID
from app.tasks.celery_app import celery_app
from sqlalchemy.orm import Session
from app.core.logging import setup_logger
from app.core.database import get_db
from app.entities.balance import BalanceEntity

logger = setup_logger("app.tasks.balance_tasks")

@celery_app.task(name="app.tasks.balance_tasks.update_balance_async")
def update_balance_async(user_id: str, ticker: str, amount: int):
    """
    Асинхронное обновление баланса пользователя
    
    Args:
        user_id: ID пользователя
        ticker: Тикер инструмента
        amount: Сумма изменения баланса
    """
    logger.info(f"Асинхронное обновление баланса: user_id={user_id}, ticker={ticker}, amount={amount}")
    db = next(get_db())
    try:
        _update_balance(db, UUID(user_id), ticker, amount)
        logger.info(f"Баланс успешно обновлен: user_id={user_id}, ticker={ticker}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении баланса: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def _update_balance(db: Session, user_id: UUID, ticker: str, amount: int) -> BalanceEntity:
    """
    Обновляет баланс пользователя напрямую без создания репозитория
    """
    # Используем блокировку FOR UPDATE для предотвращения race condition
    balance = db.query(BalanceEntity).filter(
        BalanceEntity.user_id == user_id, 
        BalanceEntity.ticker == ticker
    ).with_for_update().first()

    if balance:
        balance.amount += amount
    else:
        balance = BalanceEntity(user_id=user_id, ticker=ticker, amount=amount)
        db.add(balance)

    db.commit()
    return balance
