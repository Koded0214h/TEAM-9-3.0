from app.services.audit import safe_metadata
from app.services.exports import LIMITATION


def test_audit_metadata_removes_secrets():
    result = safe_metadata({"status": "ok", "api_secret": "hidden", "password": "hidden"})
    assert result == {"status": "ok"}


def test_report_uses_neutral_limitation_language():
    assert "does not establish" in LIMITATION
    assert "criminal conduct" in LIMITATION
