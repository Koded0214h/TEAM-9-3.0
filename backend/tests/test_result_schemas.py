import uuid

import pytest
from pydantic import ValidationError

from app.schemas.results import FigureInput, SubmissionCreate


def payload(**overrides):
    values = {
        "election_id": uuid.uuid4(),
        "contest_id": uuid.uuid4(),
        "geography_node_id": uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "form_type": "EC8A",
        "figures": [FigureInput(candidate_id=uuid.uuid4(), votes=90)],
        "valid_votes": 90,
        "rejected_ballots": 10,
        "total_votes_cast": 100,
        "accredited_voters": 120,
    }
    values.update(overrides)
    return values


def test_submission_totals_are_consistent():
    assert SubmissionCreate(**payload()).total_votes_cast == 100


def test_submission_rejects_inconsistent_totals():
    with pytest.raises(ValidationError):
        SubmissionCreate(**payload(total_votes_cast=101))
