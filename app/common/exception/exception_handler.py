from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.common.exception.errors import BaseExceptionMixin
from app.common.response.response_code import CustomResponseCode, StandardResponseCode
from app.common.response.response_schema import ResponseBase
from app.utils.trace_id import get_request_trace_id
from app.utils.serializers import MsgSpecJSONResponse


def register_exception(app: FastAPI):
    @app.exception_handler(BaseExceptionMixin)
    async def custom_exception_handler(request: Request, exc: BaseExceptionMixin):
        # Nếu code là mã HTTP chuẩn thì dùng, nếu là mã nghiệp vụ thì trả về 400
        status_code = (
            exc.code if exc.code in [400, 401, 403, 404, 422, 500, 502] else 400
        )
        content = {
            "code": exc.code,
            "msg": exc.msg,
            "data": exc.data,
            "trace_id": get_request_trace_id(request),
        }
        return MsgSpecJSONResponse(
            status_code=status_code, content=content, background=exc.background
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        content = {
            "code": StandardResponseCode.HTTP_422,
            "msg": "Validation Error",
            "data": exc.errors(),
            "trace_id": get_request_trace_id(request),
        }
        return MsgSpecJSONResponse(
            status_code=StandardResponseCode.HTTP_422, content=content
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        content = {
            "code": StandardResponseCode.HTTP_422,
            "msg": "Validation Error",
            "data": exc.errors(),
            "trace_id": get_request_trace_id(request),
        }
        return MsgSpecJSONResponse(
            status_code=StandardResponseCode.HTTP_422, content=content
        )

    @app.exception_handler(Exception)
    async def all_exception_handler(request: Request, exc: Exception):
        content = {
            "code": StandardResponseCode.HTTP_500,
            "msg": str(exc),
            "data": None,
            "trace_id": get_request_trace_id(request),
        }
        return MsgSpecJSONResponse(
            status_code=StandardResponseCode.HTTP_500, content=content
        )
