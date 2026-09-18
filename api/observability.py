import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger("api.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request outcome and timing without recording request contents."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid4().hex
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.exception(
                "request_failed method=%s path=%s duration_ms=%.2f request_id=%s",
                request.method,
                request.url.path,
                elapsed_ms,
                request_id,
            )
            raise

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed method=%s path=%s status_code=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response