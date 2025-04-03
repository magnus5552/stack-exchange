from pydantic import BaseModel
from typing import List, Any, Union


class ValidationError(BaseModel):
    loc: List[Union[str, int]]
    msg: str
    type: str


class HTTPValidationError(BaseModel):
    detail: List[ValidationError]
