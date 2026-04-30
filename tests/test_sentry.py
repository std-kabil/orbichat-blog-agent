from app.config import Settings
from app.main import create_app


def test_sentry_is_not_initialized_in_test_environment(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []

    def fake_init(*args: object, **kwargs: object) -> None:
        calls.append("called")

    monkeypatch.setattr("app.main.sentry_sdk.init", fake_init)

    create_app(Settings(app_env="test", sentry_dsn="https://example.com/1"))

    assert calls == []
