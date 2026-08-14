from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.document import DocumentCreate, DocumentRead
from app.services import document_service

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(project_id: int, db: Session = Depends(get_db)) -> list[DocumentRead]:
    return document_service.list_documents(db, project_id)


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(project_id: int, payload: DocumentCreate, db: Session = Depends(get_db)) -> DocumentRead:
    return document_service.create_manual_document(
        db,
        project_id,
        typ=payload.typ,
        titel=payload.titel,
        inhalt=payload.inhalt,
        dokumentdatum=payload.dokumentdatum,
    )


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(project_id: int, document_id: int, db: Session = Depends(get_db)) -> DocumentRead:
    return document_service.get_document(db, project_id, document_id)


@router.post("/{document_id}/reprocess", response_model=DocumentRead)
def reprocess_document(project_id: int, document_id: int, db: Session = Depends(get_db)) -> DocumentRead:
    return document_service.reprocess_document(db, project_id, document_id)
