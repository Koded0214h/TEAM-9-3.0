from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
def ready(db: Annotated[Session, Depends(get_db)]) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ok")
