from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Настройки базы данных
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres:5432/exchange"

    DB_CONN_STRING: str = ""
    DB_ECHO: bool = False
    
    # Настройки Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    # Прочие настройки
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"


settings = Settings()


@lru_cache()
def get_settings():
    return settings