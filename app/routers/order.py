from typing import Union

from fastapi import APIRouter, Path

from app.dependencies import CurrentUser
from app.models import order, base

router = APIRouter(tags=["order"])


@router.post("", response_model=base.CreateOrderResponse)
async def create_order(
        user: CurrentUser,
        order_data: Union[order.LimitOrderBody, order.MarketOrderBody],
):
    # TODO: Реализовать создание ордера
    return base.CreateOrderResponse(order_id="uuid")


@router.get("",
            response_model=list[Union[order.LimitOrder, order.MarketOrder]])
async def list_orders(user: CurrentUser):
    # TODO: Реализовать получение списка ордеров
    return []


@router.get("/{order_id}",
            response_model=Union[order.LimitOrder, order.MarketOrder])
async def get_order(
        user: CurrentUser,
        order_id: str = Path(..., format="uuid4"),
):
    # TODO: Реализовать получение ордера
    return {}


@router.delete("/{order_id}", response_model=base.Ok)
async def cancel_order(
        user: CurrentUser,
        order_id: str = Path(..., format="uuid4"),
):
    # TODO: Реализовать отмену ордера
    return base.Ok()
