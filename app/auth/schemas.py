from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    password: str

class UserInDB(BaseModel):
    id: str
    name: str
    hashed_password: str
    role: str