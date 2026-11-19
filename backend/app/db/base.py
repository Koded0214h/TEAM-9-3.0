from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import model modules so Alembic can discover their metadata.
from app.models import allocation as allocation_models  # noqa: E402, F401
from app.models import auth as auth_models  # noqa: E402, F401
from app.models import capacity as capacity_models  # noqa: E402, F401
from app.models import equipment as equipment_models  # noqa: E402, F401
from app.models import geography as geography_models  # noqa: E402, F401
from app.models import scenarios as scenario_models  # noqa: E402, F401
