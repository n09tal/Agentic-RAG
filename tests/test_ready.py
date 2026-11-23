import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.api.main import app
from backend.config import Settings, get_settings

client = TestClient(app)


@pytest.fixture
def unreachable_database():
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="postgresql://nobody:wrong@127.0.0.1:1/missing"
    )
    yield
    app.dependency_overrides.clear()


def test_ready_returns_503_when_database_is_unreachable(unreachable_database):
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unreachable"}


def test_ready_returns_200_when_database_is_up():
    try:
        get_settings()
    except ValidationError:
        pytest.skip("DATABASE_URL is not configured")
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}