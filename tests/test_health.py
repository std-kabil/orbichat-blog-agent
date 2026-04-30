from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_endpoint_returns_service_status() -> None:
    app = create_app(Settings(app_env="test", sentry_dsn=None))
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "orbichat-blog-agent",
    }


def test_root_endpoint_returns_service_status() -> None:
    app = create_app(Settings(app_env="test", sentry_dsn=None))
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "orbichat-blog-agent",
    }
