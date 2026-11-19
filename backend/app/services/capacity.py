from dataclasses import dataclass


@dataclass(frozen=True)
class LoadClassification:
    ratio: float
    label: str


def classify_load(
    voters: int, *, target: int, maximum: int, underutilized_ratio: float
) -> LoadClassification:
    ratio = voters / target
    if voters > maximum:
        label = "overloaded"
    elif voters < target * underutilized_ratio:
        label = "underutilized"
    else:
        label = "within_capacity"
    return LoadClassification(ratio=round(ratio, 4), label=label)
