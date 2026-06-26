from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
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
    cors_origins: str = "http://localhost:5173,http://localhost:8000"
    session_cookie_name: str = "oscorp_session"
    csrf_cookie_name: str = "oscorp_csrf"
    cookie_secure: bool = False
    session_absolute_minutes: int = 480
    session_idle_minutes: int = 30
    login_window_minutes: int = 15
    login_max_failures: int = 5
    admin_username: str = "admin"
    admin_password: str = Field(default="", repr=False)
    telegram_bot_token: str = Field(default="", repr=False)
    telegram_chat_id: str = Field(default="", repr=False)

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment.lower() in {"production", "real"} and not self.cookie_secure:
            raise ValueError("Secure cookies are required outside LAB")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
