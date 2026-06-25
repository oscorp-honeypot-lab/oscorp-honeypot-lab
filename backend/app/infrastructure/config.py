from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OSCORP_API_",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = "oscorp-threatlab-api"
    version: str = "0.1.0"
    environment: str = "lab"
    log_level: str = "INFO"
    database_url: str = Field(
        default=(
            "postgresql+psycopg://oscorp:oscorp123"
            "@postgres:5432/oscorp"
        ),
        repr=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
