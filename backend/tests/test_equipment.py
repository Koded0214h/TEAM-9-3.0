from app.services.equipment import allocate_stock, calculate_demand


def test_calculate_demand_uses_ceiling_and_minimum() -> None:
    assert calculate_demand(701, fixed_minimum=1, voters_per_item=350, maximum=None) == 3
    assert calculate_demand(10, fixed_minimum=2, voters_per_item=350, maximum=None) == 2


def test_calculate_demand_respects_maximum() -> None:
    assert calculate_demand(5000, fixed_minimum=1, voters_per_item=350, maximum=5) == 5


def test_allocate_stock_is_deterministic_and_finite() -> None:
    result = allocate_stock([("b", 3, 100), ("a", 4, 100), ("c", 2, 50)], available=6)
    assert [(item.polling_unit_id, item.allocated) for item in result] == [
        ("c", 2),
        ("a", 4),
        ("b", 0),
    ]
    assert sum(item.allocated for item in result) == 6
