from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus, DocumentType
from app.ingestion.pipeline import process_document
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

    # Schritt 3: synchron verarbeiten (Background-Task-Runner kommt erst in
    # Schritt 8). process_document ist bereits so gebaut, dass sie unveraendert
    # asynchron aufgerufen werden kann, sobald der Runner existiert.
    process_document(db, document.id)
    db.refresh(document)
    return document


def reprocess_document(db: Session, project_id: int, document_id: int) -> Document:
    document = get_document(db, project_id, document_id)
    process_document(db, document.id)
    db.refresh(document)
    return document
