from uuid import UUID
from enum import Enum
from pydantic import BaseModel

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"

class NewUser(BaseModel):
    name: str

class User(NewUser):
    id: UUID
    role: UserRole
    api_key: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
