import hashlib
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.background.task_runner import DocumentTaskRunner
from app.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus, DocumentType
from app.security.file_safety import (
    IMAGE_EXTENSIONS,
    build_storage_relative_path,
    looks_like_plausible_content,
    media_type_for_extension,
    validate_extension,
)
from app.services.project_service import get_project


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
    db.commit()
    db.refresh(document)

    # process_document() findet inhalt jetzt gesetzt vor und indexiert direkt
    # (review_required -> indexing), ohne die Vision-Analyse zu wiederholen.
    task_runner.enqueue(document.id)
    return document
