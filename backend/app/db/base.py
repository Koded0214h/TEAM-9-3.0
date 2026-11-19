from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import model modules so Alembic can discover their metadata.
from app.models import auth as auth_models  # noqa: E402, F401
