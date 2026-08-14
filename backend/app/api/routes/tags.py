from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.tag import TagRead
from app.services import tag_service

router = APIRouter(prefix="/api/projects/{project_id}/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def list_tags(project_id: int, db: Session = Depends(get_db)) -> list[TagRead]:
    return tag_service.list_tags(db, project_id)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(project_id: int, tag_id: int, db: Session = Depends(get_db)) -> None:
    tag_service.delete_tag(db, project_id, tag_id)
