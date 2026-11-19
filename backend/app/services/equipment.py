from dataclasses import dataclass
from math import ceil


def calculate_demand(
    voters: int, *, fixed_minimum: int, voters_per_item: int | None, maximum: int | None
) -> int:
    quantity = fixed_minimum
    if voters_per_item:
        quantity = max(quantity, ceil(voters / voters_per_item))
    return min(quantity, maximum) if maximum is not None else quantity


@dataclass(frozen=True)
class StockAllocation:
    polling_unit_id: str
    demand: int
    allocated: int


def allocate_stock(demands: list[tuple[str, int, int]], available: int) -> list[StockAllocation]:
    """Allocate by rule priority, then highest demand, then stable polling-unit ID."""
    remaining = max(available, 0)
    allocations = []
    for unit_id, demand, _priority in sorted(
        demands, key=lambda item: (item[2], -item[1], item[0])
    ):
        allocated = min(demand, remaining)
        allocations.append(StockAllocation(unit_id, demand, allocated))
        remaining -= allocated
    return allocations
