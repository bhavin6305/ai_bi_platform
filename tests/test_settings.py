import pytest
from pydantic import ValidationError

from api.routes.auth import DEFAULT_SETTINGS, SettingsUpdate, get_settings, update_settings


def test_settings_are_available_without_auth_in_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REQUIRE_AUTH", "false")

    assert get_settings(None) == {"settings": DEFAULT_SETTINGS}


def test_settings_update_is_available_without_auth_in_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REQUIRE_AUTH", "false")

    response = update_settings(SettingsUpdate(show_executive_summary=False), None)

    assert response["settings"]["show_executive_summary"] is False
    assert response["settings"]["full_name"] == "Local User"


def test_dashboard_preferences_accept_supported_values():
    settings = SettingsUpdate(default_date_range="90d", number_format="full")

    assert settings.default_date_range == "90d"
    assert settings.number_format == "full"


def test_dashboard_preferences_reject_unsupported_values():
    with pytest.raises(ValidationError):
        SettingsUpdate(default_date_range="forever")