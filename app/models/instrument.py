from pydantic import BaseModel
from pydantic import constr


class Instrument(BaseModel):
    ticker: str
    name: str
    active: bool = True

class Instrument(BaseModel):
    name: str
    ticker: constr(pattern=r"^[A-Z]{2,10}$")
