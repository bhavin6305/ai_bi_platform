from api.routes.auth import DEFAULT_SETTINGS, SettingsUpdate, get_settings, update_settings


def test_settings_are_available_without_auth_in_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REQUIRE_AUTH", "false")

    assert get_settings(None) == {"settings": DEFAULT_SETTINGS}


def test_settings_update_is_available_without_auth_in_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REQUIRE_AUTH", "false")

    response = update_settings(SettingsUpdate(compact_mode=True), None)

    assert response["settings"]["compact_mode"] is True
    assert response["settings"]["full_name"] == "Local User"