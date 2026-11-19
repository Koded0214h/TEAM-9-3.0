from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.identity import User


def main() -> None:
    settings = get_settings()
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        raise SystemExit("Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD")
    if len(settings.bootstrap_admin_password) < 12:
        raise SystemExit("Bootstrap password must contain at least 12 characters")
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)):
            raise SystemExit("Bootstrap refused because a user already exists")
        db.add(
            User(
                email=settings.bootstrap_admin_email.lower(),
                full_name="Platform Administrator",
                password_hash=hash_password(settings.bootstrap_admin_password),
                is_platform_admin=True,
            )
        )
        db.commit()
    print("Platform administrator created; enroll MFA immediately")


if __name__ == "__main__":
    main()
