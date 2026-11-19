from app.schemas.comparisons import MetricValue


def test_unavailable_metric_cannot_imply_a_value() -> None:
    metric = MetricValue(status="unavailable", explanation="No engine result")
    assert metric.scenario is None
    assert metric.baseline is None


def test_available_metric_preserves_explanation() -> None:
    metric = MetricValue(
        status="available",
        baseline=4,
        scenario=2,
        delta=-2,
        unit="polling_units",
        explanation="Capacity rule v1",
    )
    assert metric.delta == -2
