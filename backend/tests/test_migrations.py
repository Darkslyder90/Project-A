import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import get_settings

_BACKEND_DIR = Path(__file__).resolve().parents[1]

_EXPECTED_TABLES = {
    "projects",
    "documents",
    "document_tags",
    "tags",
    "people",
    "tasks",
    "task_documents",
    "meetings",
    "meeting_participants",
    "chunks",
    "index_metadata",
    "chat_conversations",
    "chat_messages",
    "api_usage_logs",
    "app_settings",
}


def test_alembic_upgrade_head_creates_expected_schema(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()

    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))

    command.upgrade(cfg, "head")

    db_path = tmp_path / "data" / "project-a.db"
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    finally:
        conn.close()
    table_names = {row[0] for row in rows}

    assert _EXPECTED_TABLES.issubset(table_names)

    get_settings.cache_clear()
