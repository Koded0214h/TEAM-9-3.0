from app.engines.simulation import StubSimulationEngine
from app.schemas.simulation import SimulationEngineResult


def test_stub_produces_no_fake_estimates() -> None:
    result = StubSimulationEngine().run({"scenario_id": "demo"})
    assert result.status == "not_implemented"
    assert result.units == []
    assert "No queue model" in result.limitations[0]


def test_simulation_result_contract_accepts_real_shape() -> None:
    result = SimulationEngineResult(
        status="succeeded",
        units=[],
        explanation="Contract fixture",
        limitations=["Illustrative assumptions"],
    )
    assert result.status == "succeeded"
