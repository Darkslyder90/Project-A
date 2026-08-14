from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.person import PersonCreate, PersonRead, PersonUpdate
from app.services import person_service

router = APIRouter(prefix="/api/projects/{project_id}/people", tags=["people"])


@router.get("", response_model=list[PersonRead])
def list_people(project_id: int, db: Session = Depends(get_db)) -> list[PersonRead]:
    return person_service.list_people(db, project_id)


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(project_id: int, payload: PersonCreate, db: Session = Depends(get_db)) -> PersonRead:
    return person_service.create_person(
        db,
        project_id,
        name=payload.name,
        rolle=payload.rolle,
        kontaktinfo=payload.kontaktinfo,
        notizen=payload.notizen,
    )


@router.get("/{person_id}", response_model=PersonRead)
def get_person(project_id: int, person_id: int, db: Session = Depends(get_db)) -> PersonRead:
    return person_service.get_person(db, project_id, person_id)


@router.patch("/{person_id}", response_model=PersonRead)
def update_person(
    project_id: int, person_id: int, payload: PersonUpdate, db: Session = Depends(get_db)
) -> PersonRead:
    return person_service.update_person(db, project_id, person_id, payload)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(project_id: int, person_id: int, db: Session = Depends(get_db)) -> None:
    person_service.delete_person(db, project_id, person_id)
