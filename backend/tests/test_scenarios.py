from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.scenarios import PollingUnitChangeCreate
from app.services.scenarios import ensure_revision


def test_revision_match_is_accepted() -> None:
    ensure_revision(SimpleNamespace(revision=3), 3)


def test_stale_revision_is_rejected() -> None:
    with pytest.raises(AppError) as error:
        ensure_revision(SimpleNamespace(revision=4), 3)
    assert error.value.code == "scenario_revision_conflict"
    assert error.value.details == {"expected": 3, "current": 4}


def test_new_proposal_requires_location_and_identity() -> None:
    with pytest.raises(ValidationError):
        PollingUnitChangeCreate(
            change_type="proposed_new", reason="New location", expected_revision=1
        )


def test_deactivation_requires_baseline_unit() -> None:
    with pytest.raises(ValidationError):
        PollingUnitChangeCreate(
            change_type="deactivated", reason="No longer suitable", expected_revision=1
        )
