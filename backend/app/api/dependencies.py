import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.auth import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise AppError(
            code="not_authenticated", message="Authentication is required", status_code=401
        )
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise AppError(
            code="invalid_token", message="Access token is invalid", status_code=401
        ) from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(
            code="inactive_user", message="User is inactive or unavailable", status_code=401
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: str) -> Callable[..., User]:
    def dependency(user: CurrentUser) -> User:
        if not ({role.name for role in user.roles} & set(allowed)):
            raise AppError(
                code="forbidden",
                message="You do not have permission for this action",
                status_code=403,
            )
        return user

    return dependency
