from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
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
    admin_api_key: SecretStr | None = None

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
    llm_model_pricing: dict[str, dict[str, Decimal]] = Field(
        default_factory=lambda: {
            "qwen/qwen3.6-plus": {"input_per_million": Decimal("0.30"), "output_per_million": Decimal("1.20")},
            "moonshotai/kimi-k2.6": {
                "input_per_million": Decimal("0.60"),
                "output_per_million": Decimal("2.50"),
            },
            "openai/gpt-5.4-mini": {
                "input_per_million": Decimal("0.25"),
                "output_per_million": Decimal("2.00"),
            },
            "openai/gpt-5.4": {"input_per_million": Decimal("2.00"), "output_per_million": Decimal("8.00")},
            "anthropic/claude-sonnet-4.6": {
                "input_per_million": Decimal("3.00"),
                "output_per_million": Decimal("15.00"),
            },
            "anthropic/claude-haiku-4.5": {
                "input_per_million": Decimal("0.80"),
                "output_per_million": Decimal("4.00"),
            },
        }
    )
    search_provider_pricing: dict[str, Decimal] = Field(
        default_factory=lambda: {
            "tavily": Decimal("0.005"),
            "exa": Decimal("0.005"),
            "brave": Decimal("0.001"),
        }
    )

    topic_scoring_model: str = "qwen/qwen3.6-plus"
    seo_angles_model: str = "moonshotai/kimi-k2.6"
    outline_model: str = "moonshotai/kimi-k2.6"
    claim_extraction_model: str = "moonshotai/kimi-k2.6"
    risky_claim_review_model: str = "openai/gpt-5.4-mini"
    publish_judgment_model: str = "openai/gpt-5.4"

    article_writing_model: str = "anthropic/claude-sonnet-4.6"
    blog_feedback_model: str = "anthropic/claude-sonnet-4.6"
    brand_polish_model: str = "anthropic/claude-sonnet-4.6"
    social_posts_model: str = "anthropic/claude-haiku-4.5"

    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    @model_validator(mode="after")
    def validate_production_admin_auth(self) -> "Settings":
        if self.app_env not in {"staging", "production"}:
            return self

        admin_api_key = self.admin_api_key.get_secret_value() if self.admin_api_key else None
        if not admin_api_key:
            raise ValueError("ADMIN_API_KEY is required in staging and production")
        if len(admin_api_key) < 32:
            raise ValueError("ADMIN_API_KEY must be at least 32 characters in staging and production")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
