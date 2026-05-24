import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from .custom import AppException

logger = logging.getLogger(__name__)


class GlobalExceptionHandlers:
    """Container for application-wide exception handlers."""

    @staticmethod
    async def app_exception_handler(request: Request, exc: AppException):
        logger.error(
            f"Handled AppException: {exc.__class__.__name__}: {exc.message}",
            extra={"path": request.url.path, "status_code": exc.status_code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @staticmethod
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": "An unexpected internal server error occurred."},
        )
