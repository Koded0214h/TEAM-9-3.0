import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_development_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production", auth_secret_key="development-only-secret-change-this")
