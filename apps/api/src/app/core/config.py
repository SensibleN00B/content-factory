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


settings = AppSettings()
