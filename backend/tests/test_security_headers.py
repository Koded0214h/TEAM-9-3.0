from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_docs_csp_allows_swagger_assets():
    response = client.get("/docs")
    policy = response.headers["content-security-policy"]
    assert response.status_code == 200
    assert "https://cdn.jsdelivr.net" in policy
    assert "connect-src 'self'" in policy


def test_api_csp_remains_restrictive():
    response = client.get("/api/v1/health/live")
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )
