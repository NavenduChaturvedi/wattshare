import pytest
from fastapi.testclient import TestClient

from backend.api.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """The real FastAPI app against a throwaway SQLite file (tmp_path / "test.db")."""
    monkeypatch.setenv("WATTSHARE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("WATTSHARE_SEED", "42")
    with TestClient(app) as c:  # the context manager runs the lifespan (DB reset + fresh simulation)
        yield c
