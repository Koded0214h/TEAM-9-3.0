from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.auth import Role, User

ROLE_DESCRIPTIONS = {
    "planning_admin": "Manage planning scenarios and recommendations",
    "operations_officer": "Manage equipment and operational simulations",
    "system_admin": "Manage users, datasets, configuration, and audit history",
    "reviewer": "Read-only access to plans and results",
}


def main() -> None:
    settings = get_settings()
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        raise SystemExit("Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD first")
    if len(settings.bootstrap_admin_password) < 12:
        raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters")
    with SessionLocal() as db:
        roles = {}
        for name, description in ROLE_DESCRIPTIONS.items():
            role = db.scalar(select(Role).where(Role.name == name))
            if role is None:
                role = Role(name=name, description=description)
                db.add(role)
            roles[name] = role
        db.flush()
        if db.scalar(select(User.id).limit(1)):
            raise SystemExit("Bootstrap refused: at least one user already exists")
        db.add(
            User(
                email=settings.bootstrap_admin_email.strip().lower(),
                full_name="System Administrator",
                password_hash=hash_password(settings.bootstrap_admin_password),
                roles=[roles["system_admin"]],
            )
        )
        db.commit()
    print("Initial system administrator created")


if __name__ == "__main__":
    main()
