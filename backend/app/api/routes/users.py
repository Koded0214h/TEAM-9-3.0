import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.errors import AppError
from app.core.security import hash_password
from app.db.session import get_db
from app.models.auth import Role, User
from app.schemas.auth import UserCreate, UserListResponse, UserResponse, UserUpdate

router = APIRouter(dependencies=[Depends(require_roles("system_admin"))])
VALID_ROLES = {"planning_admin", "operations_officer", "system_admin", "reviewer"}


def _roles(db: Session, names: set[str]) -> list[Role]:
    invalid = names - VALID_ROLES
    if invalid:
        raise AppError(
            code="invalid_roles", message="One or more roles are invalid", details=sorted(invalid)
        )
    roles = list(db.scalars(select(Role).where(Role.name.in_(names))).all())
    if len(roles) != len(names):
        raise AppError(
            code="roles_not_seeded",
            message="System roles have not been initialized",
            status_code=500,
        )
    return roles


@router.get("", response_model=UserListResponse)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> UserListResponse:
    users = list(
        db.scalars(select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)).all()
    )
    return UserListResponse(
        items=users, total=db.scalar(select(func.count()).select_from(User)) or 0
    )


@router.post("", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
    if db.scalar(select(User.id).where(User.email == payload.email)):
        raise AppError(
            code="email_in_use", message="A user with this email already exists", status_code=409
        )
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        roles=_roles(db, payload.roles),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(code="user_not_found", message="User was not found", status_code=404)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID, payload: UserUpdate, db: Annotated[Session, Depends(get_db)]
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(code="user_not_found", message="User was not found", status_code=404)
    changes = payload.model_dump(exclude_unset=True)
    if "password" in changes:
        user.password_hash = hash_password(changes.pop("password"))
    if "roles" in changes:
        user.roles = _roles(db, changes.pop("roles"))
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
