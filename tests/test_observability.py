import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.observability import RequestLoggingMiddleware


def test_request_logging_adds_correlation_id_and_logs_result(caplog):
    test_app = FastAPI()
    test_app.add_middleware(RequestLoggingMiddleware)

    @test_app.get("/probe")
    def probe():
        return {"ok": True}

    with caplog.at_level(logging.INFO, logger="api.requests"):
        response = TestClient(test_app).get("/probe")

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32
    assert "request_completed method=GET path=/probe status_code=200" in caplog.text
    assert f"request_id={request_id}" in caplog.text