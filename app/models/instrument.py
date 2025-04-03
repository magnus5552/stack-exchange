from pydantic import BaseModel, constr


class Instrument(BaseModel):
    name: str
    ticker: constr(pattern=r"^[A-Z]{2,10}$")
