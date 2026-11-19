from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)
    app_name: str = "TallyTrail API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://tallytrail:tallytrail@localhost:5432/tallytrail"
    redis_url: str = "redis://localhost:6379/0"
    auth_secret_key: str = "development-only-secret-change-this"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    totp_issuer: str = "TallyTrail"
    frontend_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:3000")]
    )
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    log_level: str = "INFO"
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    max_document_bytes: int = 20 * 1024 * 1024
    irev_enabled: bool = False
    irev_provider_base_url: str | None = None
    export_retention_days: int = 30

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment == "production":
            if len(self.auth_secret_key) < 43 or "development" in self.auth_secret_key:
                raise ValueError("Production AUTH_SECRET_KEY must be high entropy")
            if self.debug:
                raise ValueError("DEBUG must be false in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
