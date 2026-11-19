from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Repelect API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://repelect:repelect@localhost:5432/repelect"
    frontend_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:3000")]
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    auth_secret_key: str = "development-only-secret-change-me-now"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    geoapify_api_key: str | None = None

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.environment == "production":
            if len(self.auth_secret_key) < 43 or "development" in self.auth_secret_key:
                raise ValueError("Production AUTH_SECRET_KEY must be a unique high-entropy secret")
            if self.debug:
                raise ValueError("DEBUG must be false in production")
            if not self.database_url.startswith(("postgresql+psycopg://", "postgresql://")):
                raise ValueError("Production requires PostgreSQL")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
