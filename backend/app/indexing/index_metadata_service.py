from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models.index_metadata import IndexMetadata
from app.services.settings_service import get_app_settings

# Chunking-Strategie-Version: erhoehen, wenn sich die Chunking-Logik selbst
# (nicht nur ihre Parameter) grundlegend aendert - dient IndexMetadata als
# Vergleichswert, um veraltete Indizes zu erkennen (siehe Briefing).
CHUNKING_STRATEGIE_VERSION = "v1"


def get_index_metadata(db: Session, project_id: int) -> IndexMetadata:
    meta = db.get(IndexMetadata, project_id)
    if meta is None:
        raise NotFoundError(
            f"IndexMetadata fuer Projekt {project_id} fehlt (sollte bei Projekt-Anlage erzeugt werden)."
        )
    return meta


def ensure_bootstrapped(db: Session, project_id: int) -> IndexMetadata:
    """Stellt sicher, dass das Projekt einen aktiven Index hat.

    Wird beim ersten erfolgreich zu indexierenden Dokument eines Projekts
    aufgerufen: legt Version 1 mit einem Snapshot der aktuellen globalen
    Settings (Embedding-Modell, Chunking-Konfiguration) an. Ab dann sind diese
    Werte am Index "eingefroren" - spaetere Dokumente desselben Projekts nutzen
    IMMER die hier gespeicherte Konfiguration, nicht die ggf. seither
    geaenderten globalen Settings, bis ein expliziter vollstaendiger Rebuild
    (siehe indexing/reindex_service.py, spaeterer Schritt) eine neue Version
    aktiviert. Das verhindert, dass ein Index unbemerkt Chunks enthaelt, die
    mit unterschiedlichen Embedding-Modellen erzeugt wurden.
    """
    meta = get_index_metadata(db, project_id)
    if meta.active_index_version > 0:
        return meta

    app_settings = get_app_settings(db)
    meta.active_index_version = 1
    meta.active_collection_name = f"project_{project_id}_v1"
    meta.active_embedding_model_name = app_settings.embedding_model_name
    meta.active_chunking_strategie_version = CHUNKING_STRATEGIE_VERSION
    meta.active_chunk_ziel_tokens = app_settings.chunk_ziel_tokens
    meta.active_chunk_overlap_tokens = app_settings.chunk_overlap_tokens
    meta.active_index_erstellt_am = datetime.now(UTC)
    db.commit()
    db.refresh(meta)
    return meta
