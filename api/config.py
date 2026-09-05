import os
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def get_app_environment() -> str:
    """Return the active application environment."""
    value = os.getenv("APP_ENV", "development").strip().lower()
    return value or "development"


def is_production_like() -> bool:
    return get_app_environment() in {"production", "prod", "staging", "stage"}


def get_allowed_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*")
    if raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    retry_exceptions: tuple[type[Exception], ...] = (TimeoutError, ConnectionError, OSError),
    **kwargs: Any,
) -> T:
    """Retry transient failures with simple exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except retry_exceptions as exc:  # pragma: no cover - exercised via tests
            last_error = exc
            if attempt == max_attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            time.sleep(delay)

    if last_error is not None:
        raise last_error

    raise RuntimeError(f"retry_with_backoff failed for {func.__name__}")
