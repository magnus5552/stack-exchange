from fastapi import APIRouter, Query

from app.auth.service import create_user
from app.models import user, instrument, base

router = APIRouter(tags=["public"])


@router.post("/register", response_model=user.User)
async def register(new_user: user.NewUser):
    user = await create_user({"name": new_user.name})
    return user


@router.get("/instrument", response_model=list[instrument.Instrument])
async def list_instruments():
    # TODO: Реализовать получение инструментов
    return []


@router.get("/orderbook/{ticker}", response_model=base.L2OrderBook)
async def get_orderbook(
        ticker: str,
        limit: int = Query(10, gt=0, le=25)
):
    # TODO: Реализовать получение стакана
    return base.L2OrderBook(bid_levels=[], ask_levels=[])


@router.get("/transactions/{ticker}", response_model=list[base.Transaction])
async def get_transaction_history(
        ticker: str,
        limit: int = Query(10, gt=0, le=100)
):
    # TODO: Реализовать получение истории сделок
    return []
