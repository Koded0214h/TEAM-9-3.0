from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models import compliance as compliance_models  # noqa: E402, F401
from app.models import elections as election_models  # noqa: E402, F401
from app.models import identity as identity_models  # noqa: E402, F401
from app.models import organisation as organisation_models  # noqa: E402, F401
from app.models import reconciliation as reconciliation_models  # noqa: E402, F401
from app.models import results as result_models  # noqa: E402, F401
