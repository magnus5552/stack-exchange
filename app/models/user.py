from pydantic import BaseModel
from enum import Enum
from uuid import UUID


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class NewUser(BaseModel):
    name: str


class User(NewUser):
    id: UUID
    role: UserRole
    api_key: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
