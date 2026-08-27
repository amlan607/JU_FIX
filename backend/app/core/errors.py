"""Domain exceptions and the global exception handlers.

Business rules raise a ``JuFixError`` subclass instead of raising ``HTTPException``
directly. This keeps the Service layer free of web framework details and lets the
Controller layer stay lightweight (Architecture 1.5).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.responses import error_response

logger = logging.getLogger("ju_fix")


class JuFixError(Exception):
    """Base class for every expected domain failure.

    Attributes:
        status_code: The HTTP status the Controller layer should return.
        code: A stable machine readable error code.
        message: A message safe to display to the end user.
    """

    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, details: object | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ValidationError(JuFixError):
    """Raised when submitted data breaks a business validation rule."""

    status_code = 400
    code = "validation_error"


class AuthenticationError(JuFixError):
    """Raised when credentials are missing, invalid or expired."""

    status_code = 401
    code = "authentication_error"


class PermissionDeniedError(JuFixError):
    """Raised when an authenticated user lacks the required role or ownership."""

    status_code = 403
    code = "permission_denied"


class NotFoundError(JuFixError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "not_found"


class ConflictError(JuFixError):
    """Raised when an action conflicts with existing state, such as a double booking."""

    status_code = 409
    code = "conflict"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the JU_FIX exception handlers to a FastAPI application.

    Args:
        app: The FastAPI application instance to configure.
    """

    @app.exception_handler(JuFixError)
    async def handle_domain_error(_: Request, exc: JuFixError) -> JSONResponse:
        """Return the standard envelope for an expected domain failure."""
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.message, exc.code, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Translate Pydantic request validation failures into the standard envelope."""
        details = [
            {"field": ".".join(str(part) for part in err["loc"][1:]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=400,
            content=error_response("The submitted data is not valid.", "validation_error", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Wrap framework level HTTP errors such as 404 in the standard envelope."""
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(str(exc.detail), "http_error"),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        """Log an unexpected failure without leaking sensitive detail to the client."""
        logger.exception("Unhandled application error: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=error_response("An unexpected error occurred.", "internal_error"),
        )
