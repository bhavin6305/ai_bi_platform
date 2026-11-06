import pytest
from fastapi import HTTPException

from api.routes.auth import auth_enabled, ensure_session_access, require_auth


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


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class _OwnershipConnection:
    def __init__(self, owner_id):
        self.owner_id = owner_id

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params=None):
        if str(statement).lstrip().startswith("SELECT owner_user_id"):
            return _ScalarResult(self.owner_id)
        return _ScalarResult(None)


class _OwnershipEngine:
    def __init__(self, owner_id):
        self.connection = _OwnershipConnection(owner_id)

    def begin(self):
        return self.connection

    def connect(self):
        return self.connection


def test_session_access_rejects_another_accounts_session(monkeypatch):
    monkeypatch.setattr(
        "api.routes.auth.resolve_request_user",
        lambda _authorization: {"user_id": 100},
    )

    with pytest.raises(HTTPException) as error:
        ensure_session_access("another-users-session", "Bearer valid-token", _OwnershipEngine(200))

    assert error.value.status_code == 404


def test_session_access_allows_the_owning_account(monkeypatch):
    user = {"user_id": 100}
    monkeypatch.setattr("api.routes.auth.resolve_request_user", lambda _authorization: user)

    assert ensure_session_access("owned-session", "Bearer valid-token", _OwnershipEngine(100)) == user


def test_session_access_hides_legacy_unowned_sessions_from_accounts(monkeypatch):
    monkeypatch.setattr(
        "api.routes.auth.resolve_request_user",
        lambda _authorization: {"user_id": 100},
    )

    with pytest.raises(HTTPException) as error:
        ensure_session_access("legacy-unowned-session", "Bearer valid-token", _OwnershipEngine(None))

    assert error.value.status_code == 404
