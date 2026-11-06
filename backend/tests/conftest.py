import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.rate_limit import reset_rate_limits
from app.database.base import Base
import app.models  # noqa: F401
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    reset_rate_limits()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(client, email="sejal@example.com", password="Passw0rdOK", name="Sejal F"):
    return client.post("/api/auth/register", json={"email": email, "password": password, "full_name": name})


@pytest.fixture(autouse=True)
def no_real_gemini(monkeypatch):
    """Tests must never call the real Gemini API, even if backend/.env contains a key."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")


@pytest.fixture()
def fake_gemini(monkeypatch):
    """Pretend Gemini is configured. Set fake_gemini["responder"] = lambda prompt, system: "<json text>"."""
    from app.core.config import settings
    from app.services import gemini
    state: dict = {"responder": None, "calls": []}
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    def fake_generate_text(prompt, *, system=None, json_mode=False, **kwargs):
        state["calls"].append({"prompt": prompt, "system": system})
        if state["responder"] is None:
            raise gemini.GeminiError("no fake responder set")
        return state["responder"](prompt, system)

    monkeypatch.setattr(gemini, "generate_text", fake_generate_text)
    return state
