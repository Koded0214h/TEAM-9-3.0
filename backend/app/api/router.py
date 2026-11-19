from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.workspaces import router as workspace_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(workspace_router, tags=["workspaces"])
