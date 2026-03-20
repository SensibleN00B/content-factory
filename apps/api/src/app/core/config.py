import os

from pydantic import BaseModel, Field


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class AppSettings(BaseModel):
    app_name: str = "Content Factory API"
    app_version: str = "0.1.0"
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_json: bool = Field(
        default_factory=lambda: os.getenv("LOG_JSON", "true").lower() not in {"0", "false", "no"}
    )
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "sqlite+pysqlite:///./content_factory.db",
        )
    )
    reddit_client_id: str = Field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID", ""))
    reddit_client_secret: str = Field(default_factory=lambda: os.getenv("REDDIT_CLIENT_SECRET", ""))
    reddit_user_agent: str = Field(
        default_factory=lambda: os.getenv("REDDIT_USER_AGENT", "content-factory/0.1")
    )
    producthunt_client_id: str = Field(
        default_factory=lambda: os.getenv("PRODUCTHUNT_CLIENT_ID", "")
    )
    producthunt_client_secret: str = Field(
        default_factory=lambda: os.getenv("PRODUCTHUNT_CLIENT_SECRET", "")
    )
    youtube_api_key: str = Field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY", ""))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    briefing_summarizer_mode: str = Field(
        default_factory=lambda: os.getenv("BRIEFING_SUMMARIZER_MODE", "llm")
    )
    briefing_summarizer_model: str = Field(
        default_factory=lambda: os.getenv(
            "BRIEFING_SUMMARIZER_MODEL",
            os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        )
    )
    openai_api_base_url: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
    )
    briefing_summarizer_timeout_seconds: float = Field(
        default_factory=lambda: _env_float("BRIEFING_SUMMARIZER_TIMEOUT_SECONDS", 45.0)
    )
    briefing_summarizer_max_retries: int = Field(
        default_factory=lambda: _env_int("BRIEFING_SUMMARIZER_MAX_RETRIES", 2)
    )
    briefing_summarizer_retry_backoff_seconds: float = Field(
        default_factory=lambda: _env_float("BRIEFING_SUMMARIZER_RETRY_BACKOFF_SECONDS", 1.0)
    )


settings = AppSettings()
