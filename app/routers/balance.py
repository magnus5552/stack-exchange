from fastapi import APIRouter

from app.dependencies import CurrentUser, CurrentAdminUser
from app.models import base
from app.models.balance import Deposit, Withdraw

router = APIRouter(tags=["balance"])


@router.get("", response_model=dict[str, int])
async def get_balances(user: CurrentUser):
    # TODO: Реализовать получение балансов
    return {"MEMCOIN": 0, "DODGE": 100500}


@router.post("/balance/deposit", response_model=base.Ok)
async def deposit(deposit: Deposit, admin: CurrentAdminUser):
    # TODO: Реализовать пополнение баланса
    return base.Ok()


@router.post("/balance/withdraw", response_model=base.Ok)
async def withdraw(withdraw: Withdraw, admin: CurrentAdminUser):
    # TODO: Реализовать вывод средств
    return base.Ok()
