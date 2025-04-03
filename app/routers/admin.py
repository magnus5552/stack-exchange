from fastapi import APIRouter, Path

from app.dependencies import CurrentAdminUser
from app.models import user, instrument, base

router = APIRouter(tags=["admin"])


@router.delete("/user/{user_id}", response_model=user.User)
async def delete_user(
        user: CurrentAdminUser,
        user_id: str = Path(..., format="uuid4"),
):
    # TODO: Реализовать удаление пользователя
    return user.User(
        id=user_id,
        name="deleted_user",
        role=user.UserRole.USER,
        api_key="deleted"
    )


@router.post("/instrument", response_model=base.Ok)
async def add_instrument(
        admin: CurrentAdminUser,
        instrument_data: instrument.Instrument
):
    # TODO: Реализовать добавление инструмента
    return base.Ok()


@router.delete("/instrument/{ticker}", response_model=base.Ok)
async def delete_instrument(
        admin: CurrentAdminUser,
        ticker: str,
):
    # TODO: Реализовать удаление инструмента
    return base.Ok()