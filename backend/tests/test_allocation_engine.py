from app.engines.allocation import StubAllocationEngine
from app.schemas.allocation import AllocationEngineResult


def test_stub_is_explicitly_not_implemented() -> None:
    result = StubAllocationEngine().run({"scenario_id": "demo"})
    assert result.status == "not_implemented"
    assert result.allocations == []
    assert "No voter reassignment" in result.warnings[0]


def test_engine_result_contract_accepts_real_result_shape() -> None:
    result = AllocationEngineResult(
        status="succeeded",
        allocations=[],
        objective_values={"load_balance": 0.25},
        satisfied_constraints=["ward_boundary"],
        explanation="Contract fixture",
    )
    assert result.objective_values["load_balance"] == 0.25
