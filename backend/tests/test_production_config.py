import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_development_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            auth_secret_key="development-only-secret-change-me-now",
        )


def test_production_accepts_high_entropy_configuration() -> None:
    settings = Settings(
        environment="production",
        auth_secret_key="a" * 64,
        database_url="postgresql+psycopg://user:pass@db/repelect",
        debug=False,
    )
    assert settings.environment == "production"
