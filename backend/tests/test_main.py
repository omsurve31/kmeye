"""Tests for the FastAPI routes and middleware in app/main.py."""

from fastapi.testclient import TestClient

from app.config import CORS_ALLOWED_ORIGINS


def test_health_returns_ok_status(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_unknown_route_returns_404(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404


def test_health_post_method_returns_405(client: TestClient) -> None:
    response = client.post("/api/health")

    assert response.status_code == 405


def test_cors_allowed_origin_receives_allow_header(client: TestClient) -> None:
    allowed_origin = CORS_ALLOWED_ORIGINS[0]

    response = client.get("/api/health", headers={"Origin": allowed_origin})

    assert response.headers["access-control-allow-origin"] == allowed_origin


def test_cors_unknown_origin_receives_no_allow_header(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
