from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.elections import router as election_router
from app.api.routes.health import router as health_router
from app.api.routes.results import router as result_router
from app.api.routes.workspaces import router as workspace_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(workspace_router, tags=["workspaces"])
api_router.include_router(election_router, tags=["elections"])
api_router.include_router(result_router, tags=["results"])
