import pytest

from ai.sql_generator import require_groq_api_key
from api.database import build_database_url
from api.routes.upload import validate_upload_files


def test_build_database_url_uses_environment_values(monkeypatch):
    monkeypatch.setenv("DB_USER", "app_user")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setenv("DB_HOST", "prod-db")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "analytics")

    url = build_database_url()

    assert "postgresql+psycopg2://app_user:secret@prod-db:5433/analytics" in url


def test_validate_upload_files_rejects_oversized_file():
    class DummyFile:
        filename = "large.csv"

        def __init__(self):
            self.file = type("Buffer", (), {"read": lambda self, size=-1: b"x" * (30 * 1024 * 1024)})()

    with pytest.raises(ValueError, match="too large"):
        validate_upload_files([DummyFile()])


def test_require_groq_api_key_raises_when_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        require_groq_api_key()
