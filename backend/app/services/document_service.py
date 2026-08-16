import hashlib
import logging
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.api.schemas.document import DocumentUpdate
from app.background.task_runner import DocumentTaskRunner
from app.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.db.models.chunk import Chunk
from app.db.models.document import Document, DocumentTag
from app.db.models.enums import DocumentStatus, DocumentType
from app.db.models.index_metadata import IndexMetadata
from app.db.models.meeting import Meeting
from app.db.models.task import TaskDocument
from app.indexing.chroma_client import get_chroma_client, get_or_create_collection
from app.security.file_safety import (
    IMAGE_EXTENSIONS,
    build_storage_relative_path,
    looks_like_plausible_content,
    media_type_for_extension,
    validate_extension,
)
from app.services.project_service import get_project

logger = logging.getLogger(__name__)


def list_documents(db: Session, project_id: int) -> list[Document]:
    get_project(db, project_id)  # 404, falls Projekt nicht existiert
    return (
        db.query(Document)
        .filter(Document.project_id == project_id, Document.deleted_at.is_(None))
        .order_by(Document.erstellt_am.desc())
        .all()
    )


def get_document(db: Session, project_id: int, document_id: int) -> Document:
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
        )
        .first()
    )
    if document is None:
        raise NotFoundError(f"Document {document_id} wurde in Projekt {project_id} nicht gefunden.")
    return document


def update_document(
    db: Session,
    project_id: int,
    document_id: int,
    update: DocumentUpdate,
    task_runner: DocumentTaskRunner,
) -> Document:
    """Nachtraegliche Bearbeitung (siehe Briefing Punkt 6). Titel-Aenderungen
    sind trivial (nirgends denormalisiert). Typ-/Dokumentdatum-Aenderungen
    aktualisieren zusaetzlich die auf Chunk denormalisierten Kopien dieser
    Felder (fuer korrekte Quellenangaben), ohne die teure Neuindexierung
    auszulösen - anders als bei einer inhaltlichen Aenderung: "Bei jeder
    inhaltlichen Aenderung werden die bisherigen Chunks dieses Dokuments
    entfernt und aus der aktuellen Version neu erzeugt" (Briefing) - dafuer
    wird hier derselbe Status-Reset+Enqueue-Pfad wie bei "Neu indexieren"
    genutzt, process_document() macht den Rest idempotent.
    """
    document = get_document(db, project_id, document_id)
    fields = update.model_fields_set

    inhalt_changed = "inhalt" in fields and update.inhalt != document.inhalt
    metadata_changed = False

    if "titel" in fields and update.titel is not None:
        document.titel = update.titel
    if "typ" in fields and update.typ is not None and update.typ != document.typ:
        document.typ = update.typ
        metadata_changed = True
    if "dokumentdatum" in fields and update.dokumentdatum != document.dokumentdatum:
        document.dokumentdatum = update.dokumentdatum
        metadata_changed = True
    if inhalt_changed:
        document.inhalt = update.inhalt

    db.commit()
    db.refresh(document)

    if metadata_changed and not inhalt_changed:
        db.query(Chunk).filter(Chunk.document_id == document.id).update(
            {"dokumenttyp": document.typ.value, "dokumentdatum": document.dokumentdatum}
        )
        db.commit()

    if inhalt_changed:
        document.status = DocumentStatus.PENDING
        document.fehlermeldung = None
        db.commit()
        db.refresh(document)
        task_runner.enqueue(document.id)

    return document


def create_manual_document(
    db: Session,
    project_id: int,
    *,
    typ: DocumentType,
    titel: str,
    inhalt: str,
    dokumentdatum: date | None,
    task_runner: DocumentTaskRunner,
) -> Document:
    get_project(db, project_id)  # 404, falls Projekt nicht existiert (statt IntegrityError)

    document = Document(
        project_id=project_id,
        typ=typ,
        titel=titel,
        inhalt=inhalt,
        status=DocumentStatus.PENDING,
        dokumentdatum=dokumentdatum or date.today(),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Schritt 8: asynchron im Hintergrund verarbeiten - der HTTP-Request
    # blockiert nie auf Chunking/Embedding (siehe Briefing). Der Client bekommt
    # das Document sofort mit status=pending zurueck und pollt/beobachtet den
    # Fortschritt ueber GET .../documents/{id}.
    task_runner.enqueue(document.id)
    return document


def find_duplicate(db: Session, project_id: int, datei_hash: str) -> Document | None:
    return (
        db.query(Document)
        .filter(
            Document.project_id == project_id,
            Document.datei_hash == datei_hash,
            Document.deleted_at.is_(None),
        )
        .first()
    )


def create_uploaded_document(
    db: Session,
    project_id: int,
    *,
    typ: DocumentType,
    titel: str | None,
    dokumentdatum: date | None,
    original_filename: str,
    content: bytes,
    task_runner: DocumentTaskRunner,
    force_duplicate: bool = False,
) -> Document:
    """Legt ein Document aus einer hochgeladenen Datei an. Inhalt bleibt
    zunaechst leer - die eigentliche Textextraktion passiert asynchron im
    Hintergrund in process_document() (siehe Briefing: Text bleibt bei
    Textdokumenten immer der extrahierte Originaltext; Bild-Analyse kommt erst
    Schritt 9).
    """
    get_project(db, project_id)

    extension = validate_extension(original_filename)
    # Bilder sind serverseitig immer typ=bild (siehe Datenmodell/Statuskette-
    # Sonderfall Review) - unabhaengig davon, was das Formular mitschickt, damit
    # die Pipeline (siehe ingestion/pipeline.py) zuverlaessig zwischen
    # Text-Extraktion und Vision-Analyse unterscheiden kann.
    if extension in IMAGE_EXTENSIONS:
        typ = DocumentType.BILD

    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationAppError(
            f"Datei ist zu gross ({len(content) / 1_048_576:.1f} MB). "
            f"Maximum: {settings.max_upload_size_mb} MB."
        )

    if not looks_like_plausible_content(extension, content):
        raise ValidationAppError(
            "Dateiinhalt passt nicht zur Dateiendung (Format-Pruefung fehlgeschlagen)."
        )

    datei_hash = hashlib.sha256(content).hexdigest()
    if not force_duplicate:
        duplicate = find_duplicate(db, project_id, datei_hash)
        if duplicate is not None:
            raise ConflictError(
                f"Diese Datei wurde in diesem Projekt bereits hochgeladen "
                f"(Dokument '{duplicate.titel}', ID {duplicate.id}). "
                "Zum bewussten Hochladen trotzdem erneut mit force=true senden."
            )

    document = Document(
        project_id=project_id,
        typ=typ,
        titel=titel or Path(original_filename).stem,
        status=DocumentStatus.PENDING,
        # Bleibt bewusst None, wenn nicht angegeben - process_document()
        # uebernimmt es dann best-effort aus den Dateimetadaten, sonst
        # Verarbeitungszeitpunkt als Vorbelegung (siehe Briefing).
        dokumentdatum=dokumentdatum,
        dateiname=original_filename,
        datei_hash=datei_hash,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    relative_path = build_storage_relative_path(project_id, document.id, extension)
    absolute_path = settings.uploads_dir / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(content)

    document.original_dateipfad = relative_path
    db.commit()
    db.refresh(document)

    task_runner.enqueue(document.id)
    return document


def get_file_path(db: Session, project_id: int, document_id: int) -> tuple[Path, str, str]:
    """Liefert (absoluter Pfad, Media-Type, urspruenglicher Dateiname) fuer den
    sicheren Datei-Download (siehe Briefing: korrekte Content-Type-/
    Content-Disposition-Header).
    """
    document = get_document(db, project_id, document_id)
    if not document.original_dateipfad:
        raise NotFoundError(f"Document {document_id} hat keine hochgeladene Originaldatei.")

    settings = get_settings()
    absolute_path = settings.uploads_dir / document.original_dateipfad
    if not absolute_path.is_file():
        raise NotFoundError(f"Originaldatei fuer Document {document_id} wurde nicht gefunden.")

    extension = Path(document.original_dateipfad).suffix.lower()
    media_type = media_type_for_extension(extension)
    filename = document.dateiname or absolute_path.name
    return absolute_path, media_type, filename


def reprocess_document(
    db: Session, project_id: int, document_id: int, task_runner: DocumentTaskRunner
) -> Document:
    document = get_document(db, project_id, document_id)
    # Sofort auf 'pending' zuruecksetzen (statt z. B. bei 'failed' zu bleiben,
    # bis der Worker den Auftrag abholt) - konsistent mit der Statuskette und
    # gibt dem Client direktes Feedback, dass ein neuer Versuch begonnen hat.
    document.status = DocumentStatus.PENDING
    document.fehlermeldung = None
    db.commit()
    db.refresh(document)

    task_runner.enqueue(document.id)
    return document


def reprocess_all_documents(db: Session, project_id: int, task_runner: DocumentTaskRunner) -> list[Document]:
    """Projekt-weite Neuindexierung - einfache Variante: ruft reprocess_document()
    nacheinander fuer jedes Dokument des Projekts auf.

    Kein echtes Blue-Green-Rebuild (siehe IndexMetadata.rebuild_status/
    pending_index_version/pending_collection_name im Datenmodell - dort fuer
    einen spaeteren, aufwaendigeren Ausbau vorgesehen: neue Version komplett
    parallel in einer zweiten Chroma-Collection aufbauen, erst danach atomar
    umschalten). Hier wird stattdessen jedes Dokument einzeln kurz ueber die
    bestehende Pipeline neu aufgebaut (loescht+erzeugt seine Chunks in der
    aktiven Version neu) - fuer den Einzelnutzer-Betrieb ohne echte
    Nebenlaeufigkeit ausreichend: der Rest des Projekts bleibt waehrenddessen
    durchgehend abrufbar, nur das gerade verarbeitete Dokument ist kurz nicht
    durchsuchbar.
    """
    documents = list_documents(db, project_id)
    return [reprocess_document(db, project_id, document.id, task_runner) for document in documents]


def confirm_image_review(
    db: Session, project_id: int, document_id: int, *, inhalt: str, task_runner: DocumentTaskRunner
) -> Document:
    """Schliesst den Review-Schritt fuer ein Bild ab (siehe Briefing Punkt 3):
    der Nutzer bestaetigt die KI-Analyse unveraendert oder mit Korrekturen: das
    Ergebnis wird als `inhalt` gespeichert - die kanonische, primaere Grundlage
    fuer Chunking/Embedding. `ocr_text`/`ki_analyse_rohtext` bleiben als
    unveraenderte Rohdaten der urspruenglichen KI-Ausgabe erhalten.
    """
    document = get_document(db, project_id, document_id)
    if document.status != DocumentStatus.REVIEW_REQUIRED:
        raise ConflictError(
            f"Document {document_id} wartet aktuell nicht auf eine Review-Bestaetigung "
            f"(Status: {document.status.value})."
        )

    confirmed = inhalt.strip()
    if not confirmed:
        raise ValidationAppError("Der bestaetigte Inhalt darf nicht leer sein.")

    document.inhalt = confirmed
    # Sofort auf 'pending' setzen (wie bei reprocess_document) statt auf
    # review_required stehen zu lassen: der Hintergrund-Job kann schneller
    # fertig sein, als das Frontend reagieren kann. review_required ist fuer
    # das Frontend kein "aktiver" Status, den es laufend abfragt - ohne diesen
    # Wechsel wuerde die Review-Ansicht daher faelschlich stehen bleiben, obwohl
    # das Dokument im Hintergrund laengst fertig verarbeitet wurde.
    document.status = DocumentStatus.PENDING
    db.commit()
    db.refresh(document)

    # process_document() findet inhalt jetzt gesetzt vor und ueberspringt daher
    # Extraktion/Vision-Analyse, indexiert also direkt.
    task_runner.enqueue(document.id)
    return document


def delete_document(db: Session, project_id: int, document_id: int) -> None:
    """Loescht ein Dokument (siehe Briefing Punkt 6: fehlertolerante, idempotente
    Loeschstrategie statt einer unrealistischen Cross-Store-ACID-Transaktion).

    Blockiert, wenn das Dokument das Pflicht-Protokoll eines Meetings ist -
    dafuer muss stattdessen das Meeting geloescht werden (siehe meeting_service,
    das dieses Dokument dann im selben Vorgang mit entfernt).

    Ablauf: zuerst Soft-Delete (Document.deleted_at, macht das Dokument sofort
    fachlich unsichtbar - list_documents/get_document filtern bereits darauf),
    danach best-effort externe Artefakte bereinigen (TaskDocument-Verknuepfungen,
    Chunks, Chroma-Vektoren, Originaldatei). Ein erneuter Aufruf nach einem
    fehlgeschlagenen Cleanup-Schritt ist gefahrlos moeglich, jeder Schritt ist
    fuer sich idempotent.
    """
    document = get_document(db, project_id, document_id)

    blocking_meeting = db.query(Meeting).filter(Meeting.document_id == document_id).first()
    if blocking_meeting is not None:
        raise ConflictError(
            f"Dieses Dokument ist das Meeting-Protokoll von Meeting {blocking_meeting.id} "
            f"(Datum {blocking_meeting.datum}) und kann nicht separat geloescht werden - "
            "loesche stattdessen das Meeting."
        )

    document.deleted_at = datetime.now(UTC)
    db.commit()

    db.query(TaskDocument).filter(TaskDocument.document_id == document_id).delete()
    db.query(DocumentTag).filter(DocumentTag.document_id == document_id).delete()
    db.query(Chunk).filter(Chunk.document_id == document_id).delete()
    db.commit()

    settings = get_settings()
    index_meta = db.get(IndexMetadata, project_id)
    if index_meta and index_meta.active_collection_name:
        try:
            client = get_chroma_client(str(settings.chroma_dir))
            collection = get_or_create_collection(client, index_meta.active_collection_name)
            collection.delete(where={"document_id": document_id})
        except Exception:  # noqa: BLE001 - best-effort, DB-Loeschung ist bereits fachlich wirksam
            logger.exception("Chroma-Cleanup fuer Document %s fehlgeschlagen", document_id)

    if document.original_dateipfad:
        absolute_path = settings.uploads_dir / document.original_dateipfad
        absolute_path.unlink(missing_ok=True)
