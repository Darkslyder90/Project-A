import uuid
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import NotFoundError
from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus, DocumentType
from app.indexing.chroma_client import get_chroma_client, get_or_create_collection
from app.indexing.index_metadata_service import ensure_bootstrapped
from app.ingestion.chunkers.dispatch import chunk_document
from app.ingestion.embedding.embedder import get_embedder
from app.ingestion.extractors.dispatch import extract_text
from app.ingestion.vision.image_analyzer import analyze_image


def _mark_failed(db: Session, document: Document | None, message: str) -> None:
    if document is None:
        return
    document.status = DocumentStatus.FAILED
    document.fehlermeldung = message[:2000]
    db.commit()


def _cleanup_existing_chunks(
    db: Session, document: Document, index_version: int, chroma_dir: str, collection_name: str | None
) -> None:
    existing = (
        db.query(Chunk)
        .filter(Chunk.document_id == document.id, Chunk.index_version == index_version)
        .all()
    )
    if not existing:
        return
    for chunk in existing:
        db.delete(chunk)
    db.commit()

    if collection_name:
        client = get_chroma_client(chroma_dir)
        collection = get_or_create_collection(client, collection_name)
        collection.delete(where={"document_id": document.id})


def process_document(db: Session, document_id: int) -> None:
    """Fuehrt Chunking + lokales Embedding + Speicherung (SQLite + Chroma) fuer
    ein Document aus. Eigenstaendige, gekapselte Funktion (nimmt nur eine
    document_id entgegen), damit sie unveraendert von einem spaeteren
    Background-Task-Runner (Schritt 8) aufgerufen werden kann.

    Idempotent: loescht vor dem (Neu-)Aufbau konsequent alle vorhandenen Chunks
    des Documents in der aktuell aktiven Index-Version, sowohl in SQLite als
    auch in Chroma - ein wiederholter Aufruf (z. B. "Erneut verarbeiten" oder
    nach inhaltlicher Bearbeitung) erzeugt daher nie Duplikate.

    Bilder (Schritt 9) durchlaufen dieselbe Funktion, halten aber nach der
    Vision-Analyse an: `inhalt` bleibt bewusst leer, bis der Nutzer die
    KI-Analyse im Review-Schritt bestaetigt/bearbeitet (siehe
    document_service.confirm_image_review, setzt dabei status=pending und
    reiht erneut hier ein). Ein erneuter Aufruf hier findet `inhalt` dann
    bereits gesetzt vor, ueberspringt Extraktion/Vision-Analyse komplett und
    indexiert direkt, ohne die Analyse zu wiederholen.
    """
    document = db.get(Document, document_id)
    if document is None:
        raise NotFoundError(f"Document {document_id} wurde nicht gefunden.")

    settings = get_settings()
    chroma_dir = str(settings.chroma_dir)

    document.status = DocumentStatus.PROCESSING
    db.commit()

    try:
        if document.inhalt is None:
            if document.typ == DocumentType.BILD:
                if not document.original_dateipfad:
                    _mark_failed(db, document, "Bild-Dokument ohne Originaldatei.")
                    return
                extension = Path(document.original_dateipfad).suffix.lower()
                image_bytes = (settings.uploads_dir / document.original_dateipfad).read_bytes()
                analysis = analyze_image(
                    db, project_id=document.project_id, image_bytes=image_bytes, extension=extension
                )
                document.ocr_text = analysis.ocr_text
                document.ki_analyse_rohtext = analysis.ki_analyse_rohtext
                if document.dokumentdatum is None:
                    # Bilder liefern kein extrahierbares Dokumentdatum wie PDF/DOCX -
                    # Verarbeitungszeitpunkt als Vorbelegung (siehe Briefing).
                    document.dokumentdatum = date.today()
                document.status = DocumentStatus.REVIEW_REQUIRED
                db.commit()
                # Wartet jetzt auf Bestaetigung/Bearbeitung durch den Nutzer -
                # Chunking/Embedding erst nach dem Review-Schritt (siehe oben).
                return
            elif document.original_dateipfad:
                # Datei-Upload (Schritt 7): Inhalt liegt noch nicht vor, muss aus
                # der Originaldatei extrahiert werden.
                extension = Path(document.original_dateipfad).suffix.lower()
                absolute_path = settings.uploads_dir / document.original_dateipfad
                extracted = extract_text(absolute_path, extension)
                document.inhalt = extracted.text
                if document.dokumentdatum is None:
                    document.dokumentdatum = extracted.dokumentdatum or date.today()
                db.commit()
            else:
                _mark_failed(db, document, "Kein indexierbarer Inhalt vorhanden (weder Text noch Originaldatei).")
                return

        text = (document.inhalt or "").strip()
        if not text:
            _mark_failed(db, document, "Kein indexierbarer Inhalt vorhanden (Extraktion leer).")
            return

        index_meta = ensure_bootstrapped(db, document.project_id)

        _cleanup_existing_chunks(
            db, document, index_meta.active_index_version, chroma_dir, index_meta.active_collection_name
        )

        document.status = DocumentStatus.INDEXING
        db.commit()

        # Bewusst die am Index EINGEFRORENE Konfiguration verwenden (nicht die
        # ggf. seither geaenderten globalen Settings) - siehe
        # index_metadata_service.ensure_bootstrapped.
        embedder = get_embedder(index_meta.active_embedding_model_name)
        candidates = chunk_document(
            text,
            document.typ,
            embedder,
            index_meta.active_chunk_ziel_tokens,
            index_meta.active_chunk_overlap_tokens,
        )
        if not candidates:
            _mark_failed(db, document, "Chunking hat keine Textabschnitte erzeugt.")
            return

        vectors = embedder.embed_passages([c.text for c in candidates])

        chunk_rows: list[Chunk] = []
        chroma_ids: list[str] = []
        chroma_documents: list[str] = []
        chroma_metadatas: list[dict] = []

        for i, (candidate, vector) in enumerate(zip(candidates, vectors)):
            chunk_id = str(uuid.uuid4())
            chunk_rows.append(
                Chunk(
                    id=chunk_id,
                    document_id=document.id,
                    index_version=index_meta.active_index_version,
                    chunk_index=i,
                    text=candidate.text,
                    abschnitt=candidate.abschnitt,
                    dateiname=document.dateiname,
                    dokumenttyp=document.typ.value,
                    dokumentdatum=document.dokumentdatum,
                )
            )
            chroma_ids.append(chunk_id)
            chroma_documents.append(candidate.text)
            chroma_metadatas.append(
                {
                    "document_id": document.id,
                    "project_id": document.project_id,
                    "index_version": index_meta.active_index_version,
                }
            )

        db.add_all(chunk_rows)

        client = get_chroma_client(chroma_dir)
        collection = get_or_create_collection(client, index_meta.active_collection_name)
        collection.upsert(
            ids=chroma_ids, embeddings=vectors, documents=chroma_documents, metadatas=chroma_metadatas
        )

        document.status = DocumentStatus.READY
        document.fehlermeldung = None
        db.commit()
    except Exception as exc:  # noqa: BLE001 - Pipeline-Fehler duerfen den Request nie 500en lassen
        db.rollback()
        document = db.get(Document, document_id)
        _mark_failed(db, document, f"{exc.__class__.__name__}: {exc}")
