from collections.abc import Generator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


@pytest.fixture
def db_session() -> Mock:
    session = Mock()
    session.execute.return_value = Mock()
    return session


@pytest.fixture
def client(db_session: Mock) -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Mock, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
