import uuid
from contextlib import suppress

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.db.session import SessionLocal
from app.services.audit import append_audit


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        actor_id = getattr(request.state, "user_id", None)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and response.status_code < 400:
            segments = request.url.path.strip("/").split("/")
            workspace_id = None
            if "workspaces" in segments:
                with suppress(ValueError, IndexError):
                    workspace_id = uuid.UUID(segments[segments.index("workspaces") + 1])
            with SessionLocal() as db:
                append_audit(
                    db,
                    action=f"http.{request.method.lower()}",
                    entity_type="api_route",
                    entity_id=request.url.path,
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    request_id=getattr(request.state, "request_id", None),
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    metadata={"status_code": response.status_code},
                )
                db.commit()
        return response
