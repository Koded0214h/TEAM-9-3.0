from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.models.auth import RefreshSession, User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    settings = get_settings()
    raw_refresh = generate_refresh_token()
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    access_token, expires_in = create_access_token(user.id, [role.name for role in user.roles])
    db.commit()
    return TokenResponse(
        access_token=access_token, refresh_token=raw_refresh, expires_in=expires_in, user=user
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise AppError(
            code="invalid_credentials", message="Email or password is incorrect", status_code=401
        )
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    session = db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_refresh_token(payload.refresh_token)
        )
    )
    now = datetime.now(UTC)
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        raise AppError(
            code="invalid_refresh_token",
            message="Refresh token is invalid or expired",
            status_code=401,
        )
    session.revoked_at = now
    if not session.user.is_active:
        raise AppError(code="inactive_user", message="User is inactive", status_code=401)
    return _issue_tokens(db, session.user)


@router.post("/logout", status_code=204)
def logout(payload: LogoutRequest, db: Annotated[Session, Depends(get_db)]) -> None:
    session = db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_refresh_token(payload.refresh_token)
        )
    )
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.commit()


@router.get("/me", response_model=UserResponse)
def current_user(user: CurrentUser) -> User:
    return user
