from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError


class GeoapifyGeocoder:
    url = "https://api.geoapify.com/v1/geocode/search"

    def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        api_key = get_settings().geoapify_api_key
        if not api_key:
            raise AppError(
                code="geocoder_not_configured",
                message="Address search is not configured",
                status_code=503,
            )
        try:
            response = httpx.get(
                self.url,
                params={
                    "text": query,
                    "format": "json",
                    "filter": "countrycode:ng",
                    "limit": limit,
                    "apiKey": api_key,
                },
                timeout=8,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppError(
                code="geocoder_unavailable",
                message="Address search is temporarily unavailable",
                status_code=503,
            ) from exc
        return [
            {
                "address": item.get("formatted"),
                "latitude": item.get("lat"),
                "longitude": item.get("lon"),
                "confidence": item.get("rank", {}).get("confidence"),
                "provider": "geoapify",
                "attribution": "Powered by Geoapify",
            }
            for item in response.json().get("results", [])
        ]
