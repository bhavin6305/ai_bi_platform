import os
import threading
import time
import logging
from collections import defaultdict
from collections.abc import Callable 
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from api.config import is_production_like

logger = logging.getLogger(__name__)

def _positive_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


class FixedWindowRateLimiter:
    """Thread-safe per-client fixed-window request limiter."""

    def __init__(self, limit: int, window_seconds: int, clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._requests: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def check(self, client_id: str) -> tuple[bool, int]:
        now = self._clock()
        with self._lock:
            count, window_start = self._requests.get(client_id, (0, now))
            if now - window_start >= self.window_seconds:
                count, window_start = 0, now

            count += 1
            self._requests[client_id] = (count, window_start)
            retry_after = max(1, int(self.window_seconds - (now - window_start)))
            return count <= self.limit, retry_after

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()


class RedisRateLimiter:
    """Redis-backed limiter shared by all application instances."""

    def __init__(self, client, limit: int, window_seconds: int, key_prefix: str = "aibi:rate-limit"):
        self.client = client
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    def check(self, client_id: str) -> tuple[bool, int]:
        key = f"{self.key_prefix}:{client_id}"
        count = int(self.client.incr(key))
        if count == 1:
            self.client.expire(key, self.window_seconds)
        ttl = int(self.client.ttl(key))
        retry_after = max(1, ttl if ttl > 0 else self.window_seconds)
        return count <= self.limit, retry_after


class ResilientRateLimiter:
    """Use Redis when available and fall back locally during development outages."""

    def __init__(self, primary: RedisRateLimiter, fallback: FixedWindowRateLimiter):
        self.primary = primary
        self.fallback = fallback
        self._using_fallback = False

    def check(self, client_id: str) -> tuple[bool, int]:
        try:
            result = self.primary.check(client_id)
            self._using_fallback = False
            return result
        except Exception as exc:
            if is_production_like():
                raise
            if not self._using_fallback:
                logger.warning("Redis rate-limit backend unavailable; using local fallback: %s", exc)
                self._using_fallback = True
            return self.fallback.check(client_id)


def get_rate_limiter() -> FixedWindowRateLimiter | RedisRateLimiter:
    limit = _positive_int("RATE_LIMIT_REQUESTS", 60)
    window_seconds = _positive_int("RATE_LIMIT_WINDOW_SECONDS", 60)
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        if is_production_like():
            raise ValueError("REDIS_URL is required for production rate limiting")
        return FixedWindowRateLimiter(limit=limit, window_seconds=window_seconds)

    try:
        import redis

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
    except Exception as exc:
        if is_production_like():
            raise RuntimeError("Redis rate-limit backend is unavailable") from exc
        return FixedWindowRateLimiter(limit=limit, window_seconds=window_seconds)

    return ResilientRateLimiter(
        RedisRateLimiter(client, limit=limit, window_seconds=window_seconds),
        FixedWindowRateLimiter(limit=limit, window_seconds=window_seconds),
    )

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: FixedWindowRateLimiter | None = None):
        super().__init__(app)
        self.limiter = limiter or get_rate_limiter()

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        client_id = request.client.host if request.client else "unknown"
        allowed, retry_after = self.limiter.check(client_id)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)