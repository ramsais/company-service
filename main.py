import logging
import logging.config

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import AppException, app_exception_handler
from app.middleware import CorrelationIdMiddleware, CorrelationIdFilter
from app.routers import company_router
from app.services.config import settings

# ---------------------------------------------------------------------------
# Structured JSON logging
# Every log record will include: timestamp, level, logger, correlation_id,
# and the message — queryable in CloudWatch Logs Insights across all services.
# ---------------------------------------------------------------------------
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation_id": {
            "()": CorrelationIdFilter,
        }
    },
    "formatters": {
        "json": {
            "format": (
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"logger":"%(name)s","correlation_id":"%(correlation_id)s",'
                '"message":"%(message)s"}'
            ),
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["correlation_id"],
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Company Service",
    description="A microservice for managing company data with local JSON storage.",
    version=settings.SERVICE_VERSION,
)

# Correlation ID middleware must be added before any other middleware so the
# ID is available to all subsequent handlers and log statements.
app.add_middleware(CorrelationIdMiddleware)

app.add_exception_handler(AppException, app_exception_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected internal server error occurred."},
    )


app.include_router(company_router.router)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for ECS cluster service — no authentication required.
    Returns 200 only if the service is ready to serve traffic.
    """
    logger.info("Health check called")
    try:
        from app.services.storage_service import CompanyStorage
        CompanyStorage()
        logger.info(
            "Health check passed",
            extra={"service": settings.SERVICE_NAME, "version": settings.SERVICE_VERSION},
        )
        return {
            "status": "healthy",
            "service": settings.SERVICE_NAME,
            "version": settings.SERVICE_VERSION,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)},
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
