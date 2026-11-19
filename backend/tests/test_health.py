from unittest.mock import Mock

from fastapi.testclient import TestClient


def test_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_readiness_checks_database(client: TestClient, db_session: Mock) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    db_session.execute.assert_called_once()


def test_request_id_is_preserved(client: TestClient) -> None:
    response = client.get("/api/v1/health/live", headers={"X-Request-ID": "test-request"})

    assert response.headers["X-Request-ID"] == "test-request"


def test_security_headers_are_added(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"


def test_not_found_uses_standard_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/not-a-route")

    assert response.status_code == 404
    body = response.json()["error"]
    assert body["code"] == "http_404"
    assert body["message"] == "Not Found"
    assert body["request_id"] == response.headers["X-Request-ID"]
