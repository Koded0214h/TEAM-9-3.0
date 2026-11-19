import logging
import threading
import time
from collections import defaultdict, deque

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("repelect.security")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Cache-Control"] = "no-store"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    policies = {
        "/auth/": 20,
        "/locations/": 60,
        "/imports": 10,
        "/allocation-runs": 30,
        "/simulation-runs": 30,
        "/exports": 20,
    }
    _events: dict[str, deque[float]] = defaultdict(deque)
    _lock = threading.Lock()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        policy = next(
            ((fragment, limit) for fragment, limit in self.policies.items() if fragment in path),
            None,
        )
        if policy:
            fragment, limit = policy
            client = request.client.host if request.client else "unknown"
            key = f"{client}:{fragment}"
            now = time.monotonic()
            with self._lock:
                events = self._events[key]
                while events and events[0] <= now - 60:
                    events.popleft()
                if len(events) >= limit:
                    logger.warning("Rate limit exceeded for %s", fragment)
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": {
                                "code": "rate_limit_exceeded",
                                "message": "Too many requests; retry later",
                                "details": None,
                                "request_id": getattr(request.state, "request_id", None),
                            }
                        },
                        headers={"Retry-After": "60"},
                    )
                events.append(now)
        return await call_next(request)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            self._record(request, response.status_code)
        return response

    @staticmethod
    def _record(request: Request, status_code: int) -> None:
        from app.db.session import SessionLocal
        from app.models.audit import AuditEvent

        parts = [part for part in request.url.path.split("/") if part]
        resource_parts = parts[2:] if parts[:2] == ["api", "v1"] else parts
        entity_type = resource_parts[0] if resource_parts else "unknown"
        entity_id = next(
            (part for part in resource_parts[1:] if len(part) >= 32 and "-" in part), None
        )
        try:
            with SessionLocal() as db:
                db.add(
                    AuditEvent(
                        actor_id=getattr(request.state, "user_id", None),
                        action=request.method.lower(),
                        entity_type=entity_type,
                        entity_id=entity_id,
                        request_id=getattr(request.state, "request_id", None),
                        path=request.url.path,
                        status_code=status_code,
                        event_metadata={"query_keys": sorted(request.query_params.keys())},
                    )
                )
                db.commit()
        except Exception:
            logger.exception("Failed to record audit event")
