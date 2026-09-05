import pytest

from api.config import get_allowed_cors_origins, get_app_environment, retry_with_backoff


def test_get_app_environment_defaults_to_development(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    assert get_app_environment() == "development"


def test_get_allowed_cors_origins_supports_csv(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com,https://admin.example.com")

    assert get_allowed_cors_origins() == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_retry_with_backoff_retries_transient_errors():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TimeoutError("temporary network timeout")
        return "ok"

    assert retry_with_backoff(flaky, max_attempts=3) == "ok"
    assert attempts["count"] == 3
