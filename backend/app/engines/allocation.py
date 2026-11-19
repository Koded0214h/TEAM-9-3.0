from typing import Protocol

from app.schemas.allocation import AllocationEngineResult


class AllocationEngine(Protocol):
    name: str
    version: str

    def run(self, input_snapshot: dict) -> AllocationEngineResult: ...


class StubAllocationEngine:
    name = "stub-allocation-engine"
    version = "0.0.0"

    def run(self, input_snapshot: dict) -> AllocationEngineResult:
        return AllocationEngineResult(
            status="not_implemented",
            explanation=(
                "The allocation algorithm is owned by a separate workstream. "
                "This run validates and preserves the backend contract only."
            ),
            warnings=[
                "No voter reassignment was calculated.",
                "This output must not be presented as an optimization recommendation.",
            ],
        )
