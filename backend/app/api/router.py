from fastapi import APIRouter

from app.api.routes.allocation_runs import router as allocation_runs_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.capacity import router as capacity_router
from app.api.routes.comparisons import router as comparisons_router
from app.api.routes.datasets import router as datasets_router
from app.api.routes.equipment import router as equipment_router
from app.api.routes.exports import router as exports_router
from app.api.routes.geographies import router as geographies_router
from app.api.routes.health import router as health_router
from app.api.routes.locations import router as locations_router
from app.api.routes.polling_units import router as polling_units_router
from app.api.routes.scenarios import router as scenarios_router
from app.api.routes.simulation_runs import router as simulation_runs_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(allocation_runs_router, tags=["allocation-runs"])
api_router.include_router(audit_router, prefix="/audit-events", tags=["audit"])
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(capacity_router, prefix="/capacity-rules", tags=["capacity"])
api_router.include_router(comparisons_router, tags=["comparisons"])
api_router.include_router(datasets_router, prefix="/datasets", tags=["datasets"])
api_router.include_router(equipment_router, tags=["equipment"])
api_router.include_router(exports_router, tags=["exports"])
api_router.include_router(geographies_router, prefix="/geographies", tags=["geographies"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(locations_router, prefix="/locations", tags=["locations"])
api_router.include_router(polling_units_router, prefix="/polling-units", tags=["polling-units"])
api_router.include_router(scenarios_router, prefix="/scenarios", tags=["scenarios"])
api_router.include_router(simulation_runs_router, tags=["simulation"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
