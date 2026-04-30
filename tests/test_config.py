from app.config import Settings


def test_auto_publish_defaults_to_false() -> None:
    settings = Settings()

    assert settings.auto_publish is False
