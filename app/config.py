from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "orbichat-blog-agent"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/orbichat_blog_agent"
    redis_url: str = "redis://localhost:6379/0"

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    tavily_api_key: str | None = None
    exa_api_key: str | None = None
    brave_api_key: str | None = None

    payload_api_url: str | None = None
    payload_api_key: str | None = None

    cloudflare_r2_access_key_id: str | None = None
    cloudflare_r2_secret_access_key: str | None = None
    cloudflare_r2_bucket: str | None = None
    cloudflare_r2_endpoint: str | None = None

    plausible_api_key: str | None = None
    plausible_site_id: str | None = None

    sentry_dsn: str | None = None

    auto_publish: bool = False
    min_publish_score: int = 85

    agent_daily_budget_usd: Decimal = Field(default=Decimal("2.00"))
    agent_monthly_budget_usd: Decimal = Field(default=Decimal("50.00"))

    topic_scoring_model: str = "qwen/qwen3.6-plus"
    seo_angles_model: str = "moonshotai/kimi-k2.6"
    outline_model: str = "moonshotai/kimi-k2.6"
    claim_extraction_model: str = "moonshotai/kimi-k2.6"
    risky_claim_review_model: str = "openai/gpt-5.4-mini"
    publish_judgment_model: str = "openai/gpt-5.4"

    article_writing_model: str = "anthropic/claude-sonnet-4.6"
    brand_polish_model: str = "anthropic/claude-sonnet-4.6"
    social_posts_model: str = "anthropic/claude-haiku-4.5"

    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
