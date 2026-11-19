from typing import Protocol

from app.schemas.simulation import SimulationEngineResult


class SimulationEngine(Protocol):
    name: str
    version: str

    def run(self, input_snapshot: dict) -> SimulationEngineResult: ...


class StubSimulationEngine:
    name = "stub-simulation-engine"
    version = "0.0.0"

    def run(self, input_snapshot: dict) -> SimulationEngineResult:
        return SimulationEngineResult(
            status="not_implemented",
            explanation=(
                "The queue/capacity simulation is owned by a separate workstream. "
                "This run validates and preserves the backend contract only."
            ),
            limitations=["No queue model has been executed."],
            warnings=["No waiting-time or capacity estimate was generated."],
        )
