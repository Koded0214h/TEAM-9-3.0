import pytest
from pydantic import ValidationError

from app.schemas.reconciliation import CommentCreate, DiscrepancyUpdate


def test_neutral_investigation_language_is_accepted():
    item = DiscrepancyUpdate(status="resolved", resolution_note="Corrected transcription")
    assert item.status == "resolved"


def test_criminal_conclusion_is_rejected():
    with pytest.raises(ValidationError):
        CommentCreate(body="This proves fraud")
