"""통일된 에러 응답.

모든 에러는 아래 형식으로 내려가요.
{"error": {"code": "INSUFFICIENT_BALANCE", "message": "토큰이 부족해요", "details": {}}}
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


_HTTP_CODES = {
    400: ("BAD_REQUEST", "요청 형식이 올바르지 않아요"),
    401: ("UNAUTHORIZED", "로그인이 필요해요"),
    403: ("FORBIDDEN", "권한이 없어요"),
    404: ("NOT_FOUND", "찾을 수 없어요"),
    405: ("METHOD_NOT_ALLOWED", "허용되지 않은 요청이에요"),
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "reason": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            _body("VALIDATION_ERROR", "입력값을 다시 확인해 주세요", {"fields": fields}),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = _HTTP_CODES.get(exc.status_code, ("HTTP_ERROR", str(exc.detail)))
        return JSONResponse(_body(code, message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(
            _body("INTERNAL_ERROR", "잠시 문제가 생겼어요. 다시 시도해 주세요"),
            status_code=500,
        )
