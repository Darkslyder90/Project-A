from sqlalchemy import text
from sqlalchemy.engine import Connection

# Identischer Aufbau wie in der Alembic-Migration c7e2a1f4d9b3 (siehe dort fuer
# die ausfuehrliche Begruendung). Bewusst hier als eigene, idempotente Kopie
# gehalten statt die Migration zu importieren - Migrationen sollen ein
# eingefrorener historischer Schritt bleiben, unabhaengig von spaeteren
# Aenderungen an diesem Modul. Wird von Tests genutzt, die das Schema direkt
# aus Base.metadata erzeugen (ohne Alembic zu durchlaufen, siehe conftest.py).
_CHUNK_FTS_DDL_STATEMENTS = [
    "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(text, content='chunks', content_rowid='rowid')",
    """
    CREATE TRIGGER IF NOT EXISTS chunks_fts_ai AFTER INSERT ON chunks BEGIN
        INSERT INTO chunk_fts(rowid, text) VALUES (new.rowid, new.text);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS chunks_fts_ad AFTER DELETE ON chunks BEGIN
        INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES ('delete', old.rowid, old.text);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS chunks_fts_au AFTER UPDATE ON chunks BEGIN
        INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES ('delete', old.rowid, old.text);
        INSERT INTO chunk_fts(rowid, text) VALUES (new.rowid, new.text);
    END
    """,
]


def ensure_chunk_fts(connection: Connection) -> None:
    for statement in _CHUNK_FTS_DDL_STATEMENTS:
        connection.execute(text(statement))
