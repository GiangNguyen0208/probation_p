"""Global exception handlers producing the standard error envelope.

Every error response from the API is wrapped in the shape
`{ "error": { "code": ..., "message": ..., "details": ... } }` from
`social_common.envelope.ErrorResponse`. Route handlers raise
`HTTPException` with a `detail` dict of `{ "code": ..., "message": ... }`
and this module normalizes those into the envelope.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from social_common.envelope import ErrorDetail, ErrorResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging_setup import get_logger

logger = get_logger("social_api_gateway.errors")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _on_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            error = ErrorDetail(
                code=exc.detail["code"],
                message=exc.detail.get("message", "Request failed."),
                details=exc.detail.get("details"),
            )
        else:
            error = ErrorDetail(
                code=f"http_{exc.status_code}",
                message=str(exc.detail) if exc.detail is not None else "Request failed.",
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error=error).model_dump(),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="validation_error",
                    message="Request validation failed.",
                    details={"errors": exc.errors()},
                )
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def _on_unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("request.unhandled_exception", path=str(request.url))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="internal_error",
                    message="An internal error occurred.",
                )
            ).model_dump(),
        )
