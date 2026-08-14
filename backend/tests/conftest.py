from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.db import models  # noqa: F401  (registriert alle Modelle bei Base.metadata)
from app.db.base import Base
from app.db.fts_setup import ensure_chunk_fts
from app.main import create_app

_REPO_ROOT = Path(__file__).resolve().parents[2]
# Geteilter, bereits befuellter Modell-Cache (siehe config.py) - vermeidet einen
# erneuten ~1GB-Download bei jedem Testlauf, obwohl data_dir pro Test isoliert ist.
_SHARED_EMBEDDING_CACHE = _REPO_ROOT / "data-dev" / "embedding-model-cache"


@pytest.fixture
def test_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    # Ueber Env-Vars + get_settings.cache_clear() statt direktem Settings(...),
    # damit sowohl die App (via create_app(settings)) als auch Code, der
    # get_settings() unabhaengig davon aufruft (z. B. ingestion/pipeline.py,
    # embedder.py - Prozess-weite Singletons), garantiert dieselbe,
    # testisolierte Konfiguration sieht statt zweier auseinanderlaufender
    # Settings-Instanzen.
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("EMBEDDING_MODEL_CACHE_DIR_OVERRIDE", str(_SHARED_EMBEDDING_CACHE))
    # Fake-Key: reicht, damit claude_client._resolve_api_key() nicht mit
    # ClaudeUnavailableError abbricht. Der eigentliche Anthropic-Client wird in
    # Chat-Tests ohnehin gemockt (siehe tests/test_chat.py) - es geht hier nur
    # nie ein echter Request raus.
    monkeypatch.setenv("CLAUDE_API_KEY", "test-fake-key")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def app(test_settings: Settings):
    application = create_app(test_settings)
    Base.metadata.create_all(bind=application.state.engine)
    # chunk_fts (FTS5-Virtual-Table + Sync-Trigger, siehe Schritt 10) ist kein
    # ORM-Modell und entsteht daher nicht ueber Base.metadata.create_all,
    # sondern ueber dieselbe idempotente DDL wie in der Alembic-Migration.
    with application.state.engine.begin() as connection:
        ensure_chunk_fts(connection)
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c
