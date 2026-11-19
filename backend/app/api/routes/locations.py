from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser
from app.services.geocoding import GeoapifyGeocoder

router = APIRouter()


@router.get("/search")
def search_locations(
    _: CurrentUser,
    q: Annotated[str, Query(min_length=3, max_length=300)],
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> list[dict[str, Any]]:
    return GeoapifyGeocoder().search(q, limit=limit)
