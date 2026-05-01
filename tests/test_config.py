import pytest

from app.config import Settings


def test_auto_publish_defaults_to_false() -> None:
    settings = Settings()

    assert settings.auto_publish is False


def test_admin_api_key_is_required_in_production() -> None:
    with pytest.raises(ValueError, match="ADMIN_API_KEY is required"):
        Settings(app_env="production")


def test_production_admin_api_key_must_be_long_enough() -> None:
    with pytest.raises(ValueError, match="ADMIN_API_KEY must be at least 32 characters"):
        Settings(app_env="production", admin_api_key="short")
