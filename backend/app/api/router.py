from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.datasets import router as datasets_router
from app.api.routes.geographies import router as geographies_router
from app.api.routes.health import router as health_router
from app.api.routes.locations import router as locations_router
from app.api.routes.polling_units import router as polling_units_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(datasets_router, prefix="/datasets", tags=["datasets"])
api_router.include_router(geographies_router, prefix="/geographies", tags=["geographies"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(locations_router, prefix="/locations", tags=["locations"])
api_router.include_router(polling_units_router, prefix="/polling-units", tags=["polling-units"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
