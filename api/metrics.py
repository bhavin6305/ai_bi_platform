import logging
import re
import threading
import time
from collections import Counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response


logger = logging.getLogger("api.metrics")
_DYNAMIC_PATH = re.compile(r"/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}|/\d+")


def metric_path(path: str) -> str:
    return _DYNAMIC_PATH.sub("/:id", path)


class MetricsRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._requests = Counter()
        self._durations = Counter()

    def record(self, method: str, path: str, status_code: int, duration_seconds: float) -> None:
        path = metric_path(path)
        status_class = f"{status_code // 100}xx"
        bucket = "le_0_5" if duration_seconds <= 0.5 else "le_2" if duration_seconds <= 2 else "gt_2"
        with self._lock:
            self._requests[(method, path, status_class)] += 1
            self._durations[(method, path, bucket)] += 1

    def render(self) -> str:
        lines = [
            "# HELP aibi_http_requests_total HTTP requests by method, path, and status class.",
            "# TYPE aibi_http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status_class), count in sorted(self._requests.items()):
                lines.append(
                    f'aibi_http_requests_total{{method="{method}",path="{path}",status_class="{status_class}"}} {count}'
                )
            lines.extend([
                "# HELP aibi_http_request_duration_bucket HTTP request duration buckets.",
                "# TYPE aibi_http_request_duration_bucket counter",
            ])
            for (method, path, bucket), count in sorted(self._durations.items()):
                lines.append(
                    f'aibi_http_request_duration_bucket{{method="{method}",path="{path}",bucket="{bucket}"}} {count}'
                )
        return "\n".join(lines) + "\n"


registry = MetricsRegistry()


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics: MetricsRegistry = registry):
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - started
        self.metrics.record(request.method, request.url.path, response.status_code, duration)
        if response.status_code == 429 or response.status_code >= 500:
            logger.warning(
                "request_alert method=%s path=%s status_code=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                duration * 1000,
            )
        return response


def metrics_response() -> PlainTextResponse:
    return PlainTextResponse(registry.render(), media_type="text/plain; version=0.0.4")