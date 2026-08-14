from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_task_runner
from app.api.schemas.document import DocumentCreate, DocumentRead, DocumentReviewSubmit
from app.background.task_runner import DocumentTaskRunner
from app.db.models.enums import DocumentType
from app.services import document_service

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(project_id: int, db: Session = Depends(get_db)) -> list[DocumentRead]:
    return document_service.list_documents(db, project_id)


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(
    project_id: int,
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    task_runner: DocumentTaskRunner = Depends(get_task_runner),
) -> DocumentRead:
    return document_service.create_manual_document(
        db,
        project_id,
        typ=payload.typ,
        titel=payload.titel,
        inhalt=payload.inhalt,
        dokumentdatum=payload.dokumentdatum,
        task_runner=task_runner,
    )


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    typ: DocumentType = Form(...),
    titel: str | None = Form(default=None),
    dokumentdatum: date | None = Form(default=None),
    force: bool = Form(default=False),
    db: Session = Depends(get_db),
    task_runner: DocumentTaskRunner = Depends(get_task_runner),
) -> DocumentRead:
    content = await file.read()
    return document_service.create_uploaded_document(
        db,
        project_id,
        typ=typ,
        titel=titel,
        dokumentdatum=dokumentdatum,
        original_filename=file.filename or "upload",
        content=content,
        force_duplicate=force,
        task_runner=task_runner,
    )


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(project_id: int, document_id: int, db: Session = Depends(get_db)) -> DocumentRead:
    return document_service.get_document(db, project_id, document_id)


@router.get("/{document_id}/file")
def download_document_file(
    project_id: int, document_id: int, db: Session = Depends(get_db)
) -> FileResponse:
    path, media_type, filename = document_service.get_file_path(db, project_id, document_id)
    return FileResponse(path=path, media_type=media_type, filename=filename)


@router.post("/{document_id}/reprocess", response_model=DocumentRead)
def reprocess_document(
    project_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    task_runner: DocumentTaskRunner = Depends(get_task_runner),
) -> DocumentRead:
    return document_service.reprocess_document(db, project_id, document_id, task_runner)


@router.post("/{document_id}/review", response_model=DocumentRead)
def confirm_document_review(
    project_id: int,
    document_id: int,
    payload: DocumentReviewSubmit,
    db: Session = Depends(get_db),
    task_runner: DocumentTaskRunner = Depends(get_task_runner),
) -> DocumentRead:
    return document_service.confirm_image_review(
        db, project_id, document_id, inhalt=payload.inhalt, task_runner=task_runner
    )
