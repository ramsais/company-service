import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Reads X-Correlation-ID from the incoming request (set by API Gateway / ALB or
    a calling service).  If absent, generates a new UUID.

    The ID is:
      - Stored on request.state.correlation_id for use anywhere in the request lifecycle.
      - Injected into every log record via a logging Filter so all log lines for a
        request carry the same correlation_id field — enabling end-to-end tracing
        across services in CloudWatch Logs Insights.
      - Echoed back in the response header so downstream callers can correlate too.
    """

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        # Inject into log context for the duration of this request
        _correlation_ctx.set(correlation_id)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        response.headers[CORRELATION_ID_HEADER] = correlation_id

        logger.info(
            "request completed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


# ---------------------------------------------------------------------------
# Context-var based storage so the correlation ID is available in any log
# record emitted during a request, even from nested service calls.
# ---------------------------------------------------------------------------
from contextvars import ContextVar

_correlation_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")


class CorrelationIdFilter(logging.Filter):
    """Adds correlation_id field to every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_ctx.get("-")
        return True
