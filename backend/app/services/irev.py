from dataclasses import dataclass

from app.core.config import get_settings
from app.core.errors import AppError


@dataclass(frozen=True)
class IReVProviderConfig:
    base_url: str
    timeout_seconds: int = 20
    max_attempts: int = 3


def approved_provider() -> IReVProviderConfig:
    settings = get_settings()
    if not settings.irev_enabled or not settings.irev_provider_base_url:
        raise AppError(
            "irev_provider_disabled",
            "Automated IReV retrieval is disabled; use the manual public-document import",
            503,
        )
    return IReVProviderConfig(base_url=settings.irev_provider_base_url)


def fetch_public_record(_external_reference: str) -> bytes:
    approved_provider()
    raise AppError(
        "irev_adapter_not_approved",
        "No automated endpoint contract has been approved; manual import remains available",
        501,
    )
