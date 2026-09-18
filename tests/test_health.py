from fastapi.testclient import TestClient

import api.main


def test_readiness_returns_ok_when_database_is_available(monkeypatch):
    monkeypatch.setattr(api.main, "test_connection", lambda: True)

    response = TestClient(api.main.app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"ready": True, "database": "ok"}


def test_readiness_returns_service_unavailable_when_database_is_down(monkeypatch):
    monkeypatch.setattr(api.main, "test_connection", lambda: False)

    response = TestClient(api.main.app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {"ready": False, "database": "error"}