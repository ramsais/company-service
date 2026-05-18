from app.logging_config import configure_logging, RequestLoggingMiddleware

# Must be the very first call — before FastAPI app is created
configure_logging(level="INFO")

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import AppException, app_exception_handler
from app.routers import company_router
from app.services.config import settings

logger = logging.getLogger("company_service")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Company Service",
    description="A microservice for managing company data with local JSON storage.",
    version=settings.SERVICE_VERSION,
)

# RequestLoggingMiddleware must be added first so correlation_id is set
# before any other middleware or handler runs.
app.add_middleware(RequestLoggingMiddleware)

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
