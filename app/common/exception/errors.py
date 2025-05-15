from typing import Any, Optional
from fastapi import HTTPException
from starlette.background import BackgroundTask
from app.common.response.response_code import CustomErrorCode, StandardResponseCode


class BaseExceptionMixin(Exception):
    code: int

    def __init__(
        self,
        msg: str = None,
        data: Any = None,
        background: Optional[BackgroundTask] = None,
    ):
        self.msg = msg
        self.data = data
        self.background = background


class HTTPError(HTTPException):
    def __init__(
        self, code: int, msg: Any = None, headers: Optional[dict[str, Any]] = None
    ):
        super().__init__(status_code=code, detail=msg, headers=headers)


class CustomError(BaseExceptionMixin):
    def __init__(
        self, error: dict, data: Any = None, background: Optional[BackgroundTask] = None
    ):
        self.code = error["code"]
        super().__init__(msg=error["msg"], data=data, background=background)


class RequestError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_400

    def __init__(
        self,
        msg: str = "Bad Request",
        data: Any = None,
        background: Optional[BackgroundTask] = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class ForbiddenError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_403

    def __init__(
        self,
        msg: str = "Forbidden",
        data: Any = None,
        background: Optional[BackgroundTask] = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class NotFoundError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_404

    def __init__(
        self,
        msg: str = "Not Found",
        data: Any = None,
        background: Optional[BackgroundTask] = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class ServerError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_500

    def __init__(
        self,
        msg: str = "Internal Server Error",
        data: Any = None,
        background: Optional[BackgroundTask] = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class GatewayError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_502

    def __init__(
        self,
        msg: str = "Bad Gateway",
        data: Any = None,
        background: Optional[BackgroundTask] = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class AuthorizationError(BaseExceptionMixin):
    code = StandardResponseCode.HTTP_401

    def __init__(
        self,
        msg: str = "Permission Denied",
        data: Any = None,
        background: Optional[BackgroundTask] = None,
    ):
        super().__init__(msg=msg, data=data, background=background)


class TokenError(HTTPError):
    code = StandardResponseCode.HTTP_401

    def __init__(
        self, msg: str = "Not Authenticated", headers: Optional[dict[str, Any]] = None
    ):
        super().__init__(
            code=self.code, msg=msg, headers=headers or {"WWW-Authenticate": "Bearer"}
        )
