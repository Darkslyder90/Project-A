from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.db.models.enums import TaskStatus
from app.services import task_service

router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(
    project_id: int, status_filter: TaskStatus | None = None, db: Session = Depends(get_db)
) -> list[TaskRead]:
    return task_service.list_tasks(db, project_id, status_filter)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(project_id: int, payload: TaskCreate, db: Session = Depends(get_db)) -> TaskRead:
    return task_service.create_task(
        db,
        project_id,
        titel=payload.titel,
        beschreibung=payload.beschreibung,
        status=payload.status,
        zugewiesen_an=payload.zugewiesen_an,
        faellig_am=payload.faellig_am,
        dokument_ids=payload.dokument_ids,
    )


@router.get("/{task_id}", response_model=TaskRead)
def get_task(project_id: int, task_id: int, db: Session = Depends(get_db)) -> TaskRead:
    return task_service.get_task(db, project_id, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    project_id: int, task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)
) -> TaskRead:
    return task_service.update_task(db, project_id, task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(project_id: int, task_id: int, db: Session = Depends(get_db)) -> None:
    task_service.delete_task(db, project_id, task_id)


@router.post("/{task_id}/documents/{document_id}", response_model=TaskRead)
def link_document(
    project_id: int, task_id: int, document_id: int, db: Session = Depends(get_db)
) -> TaskRead:
    return task_service.link_document(db, project_id, task_id, document_id)


@router.delete("/{task_id}/documents/{document_id}", response_model=TaskRead)
def unlink_document(
    project_id: int, task_id: int, document_id: int, db: Session = Depends(get_db)
) -> TaskRead:
    return task_service.unlink_document(db, project_id, task_id, document_id)
