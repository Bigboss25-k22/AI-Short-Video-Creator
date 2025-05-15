from pydantic import BaseModel
from typing import Any, Optional


class ResponseBase(BaseModel):
    code: int
    msg: str
    data: Optional[Any] = None
    trace_id: Optional[str] = None

    @classmethod
    def success(cls, data: Any = None) -> "ResponseBase":
        return cls(code=200, msg="Success", data=data)

    @classmethod
    def fail(cls, res: dict, data: Any = None) -> "ResponseBase":
        return cls(code=res["code"], msg=res["msg"], data=data)
