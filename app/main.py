from fastapi import FastAPI
from app.routers import public, balance, order, admin

app = FastAPI(
    title="Stock Exchange",
    version="0.1.0",
    openapi_url="/openapi.json",
    root_path="/api/v1"
)

app.include_router(public.router, prefix="/public")
app.include_router(balance.router, prefix="/balance")
app.include_router(order.router, prefix="/order")
app.include_router(admin.router, prefix="/admin")
