import os

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    app_name: str = "Content Factory API"
    app_version: str = "0.1.0"
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


settings = AppSettings()
