from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "e725c52cb69f9d31084edc201d6327103323084e3b848db92b7c7bac3b72e516"
    ALGORITHM: str = "HS256"
    AUTH_SCHEME: str = "Bearer"

    DB_CONN_STRING: str = ""
    DB_ECHO: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
