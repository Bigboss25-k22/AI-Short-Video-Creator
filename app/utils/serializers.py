from starlette.responses import JSONResponse
from typing import Any, Optional
from starlette.background import BackgroundTask


class MsgSpecJSONResponse(JSONResponse):
    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        background: Optional[BackgroundTask] = None,
    ) -> None:
        super().__init__(
            content=content,
            status_code=status_code,
            background=background,
            media_type="application/json",
        )
