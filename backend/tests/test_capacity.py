import pytest
from pydantic import ValidationError

from app.schemas.capacity import CapacityRuleCreate
from app.services.capacity import classify_load


def test_classifies_overloaded_unit() -> None:
    result = classify_load(1200, target=700, maximum=1000, underutilized_ratio=0.5)
    assert result.label == "overloaded"
    assert result.ratio == 1.7143


def test_classifies_underutilized_unit() -> None:
    assert (
        classify_load(300, target=700, maximum=1000, underutilized_ratio=0.5).label
        == "underutilized"
    )


def test_classifies_unit_within_capacity() -> None:
    assert (
        classify_load(700, target=700, maximum=1000, underutilized_ratio=0.5).label
        == "within_capacity"
    )


def test_maximum_cannot_be_below_target() -> None:
    with pytest.raises(ValidationError):
        CapacityRuleCreate(
            version="v1",
            target_voters=800,
            maximum_voters=700,
            underutilized_ratio=0.5,
            explanation="Invalid rule",
        )
