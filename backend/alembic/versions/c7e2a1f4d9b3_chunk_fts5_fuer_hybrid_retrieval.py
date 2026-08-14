"""chunk_fts5 fuer hybrid retrieval

Revision ID: c7e2a1f4d9b3
Revises: 931b876860b6
Create Date: 2026-08-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e2a1f4d9b3"
down_revision: Union[str, Sequence[str], None] = "931b876860b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    FTS5-Virtual-Table + Sync-Trigger sind kein SQLAlchemy-ORM-Konstrukt und
    werden daher als rohes SQL angelegt (siehe Briefing: chunk_fts fuer
    Document-/Chunk-Inhalte, getrennt von person_fts/task_fts). 'external
    content'-Tabelle ueber chunks.rowid (SQLites impliziter Rowid existiert
    auch bei TEXT-Primary-Key wie Chunk.id) - vermeidet doppelte Textspeicherung.
    Trigger halten den Index bei INSERT/UPDATE/DELETE auf chunks automatisch
    synchron, unabhaengig davon ob die Aenderung aus process_document() oder
    einem DB-seitigen ON DELETE CASCADE (Document-Loeschung) stammt.
    """
    op.execute("CREATE VIRTUAL TABLE chunk_fts USING fts5(text, content='chunks', content_rowid='rowid')")

    op.execute(
        """
        CREATE TRIGGER chunks_fts_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunk_fts(rowid, text) VALUES (new.rowid, new.text);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER chunks_fts_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES ('delete', old.rowid, old.text);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER chunks_fts_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES ('delete', old.rowid, old.text);
            INSERT INTO chunk_fts(rowid, text) VALUES (new.rowid, new.text);
        END
        """
    )

    # Backfill fuer bereits vorhandene Chunks (z. B. lokale Dev-Datenbanken mit
    # Daten aus Schritt 3-9, die vor diesem Index angelegt wurden).
    op.execute("INSERT INTO chunk_fts(rowid, text) SELECT rowid, text FROM chunks")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS chunks_fts_au")
    op.execute("DROP TRIGGER IF EXISTS chunks_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS chunks_fts_ai")
    op.execute("DROP TABLE IF EXISTS chunk_fts")
