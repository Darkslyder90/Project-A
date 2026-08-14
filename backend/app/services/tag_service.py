from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models.document import Document, DocumentTag
from app.db.models.tag import Tag
from app.services.document_service import get_document
from app.services.project_service import get_project


def list_tags(db: Session, project_id: int) -> list[Tag]:
    get_project(db, project_id)  # 404, falls Projekt nicht existiert
    return db.query(Tag).filter(Tag.project_id == project_id).order_by(Tag.name).all()


def get_or_create_tag(db: Session, project_id: int, name: str) -> Tag:
    """Tags sind eine eigene, verbindliche Tabelle (siehe Briefing) statt
    kommaseparierter Strings - beim Zuweisen an ein Dokument wird ein Tag mit
    demselben Namen im Projekt wiederverwendet statt dupliziert (Unique-
    Constraint auf (project_id, name)).
    """
    get_project(db, project_id)
    normalized = name.strip()

    existing = db.query(Tag).filter(Tag.project_id == project_id, Tag.name == normalized).first()
    if existing is not None:
        return existing

    tag = Tag(project_id=project_id, name=normalized)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, project_id: int, tag_id: int) -> None:
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.project_id == project_id).first()
    if tag is None:
        raise NotFoundError(f"Tag {tag_id} wurde in Projekt {project_id} nicht gefunden.")
    db.delete(tag)  # DocumentTag-Zeilen raeumt die FK-Kaskade mit auf
    db.commit()


def assign_tag(db: Session, project_id: int, document_id: int, tag_name: str) -> Document:
    """Ein Document darf ausschliesslich Tags desselben Projekts referenzieren
    (siehe Briefing) - durch get_or_create_tag(project_id, ...) strukturell
    sichergestellt, statt eine beliebige tag_id entgegenzunehmen.
    """
    document = get_document(db, project_id, document_id)
    tag = get_or_create_tag(db, project_id, tag_name)

    existing = db.get(DocumentTag, (document_id, tag.id))
    if existing is None:
        db.add(DocumentTag(document_id=document_id, tag_id=tag.id))
        db.commit()
        db.refresh(document)
    return document


def unassign_tag(db: Session, project_id: int, document_id: int, tag_id: int) -> Document:
    document = get_document(db, project_id, document_id)

    link = db.get(DocumentTag, (document_id, tag_id))
    if link is not None:
        db.delete(link)
        db.commit()
        db.refresh(document)
    return document
