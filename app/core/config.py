from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Настройки базы данных
    DATABASE_URL: Optional[str] = None
    DB_CONN_STRING: str
    DB_ECHO: bool = False
    
    # Настройки Redis
    REDIS_HOST: str
    REDIS_PORT: int
    
    # Настройки безопасности
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Токен администратора (если задан, будет использоваться при создании админа)
    ADMIN_TOKEN: Optional[str] = None

    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()