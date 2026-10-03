import pytest
from fastapi import HTTPException

from api.routes.auth import auth_enabled, require_auth


def test_auth_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("REQUIRE_AUTH", raising=False)
    monkeypatch.setenv("APP_ENV", "development")

    assert auth_enabled() is False
    assert require_auth(None) is None


def test_require_auth_rejects_missing_bearer_when_enabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("REQUIRE_AUTH", "true")

    with pytest.raises(HTTPException, match="Authentication required"):
        require_auth(None)


def test_auth_cannot_be_disabled_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("REQUIRE_AUTH", "false")

    assert auth_enabled() is True


def test_auth_can_be_enabled_explicitly_in_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REQUIRE_AUTH", "true")

    assert auth_enabled() is True
