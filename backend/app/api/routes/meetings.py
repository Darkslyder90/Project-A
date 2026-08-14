from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.meeting import MeetingCreate, MeetingRead, MeetingUpdate
from app.services import meeting_service

router = APIRouter(prefix="/api/projects/{project_id}/meetings", tags=["meetings"])


@router.get("", response_model=list[MeetingRead])
def list_meetings(project_id: int, db: Session = Depends(get_db)) -> list[MeetingRead]:
    return meeting_service.list_meetings(db, project_id)


@router.post("", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
def create_meeting(project_id: int, payload: MeetingCreate, db: Session = Depends(get_db)) -> MeetingRead:
    return meeting_service.create_meeting(
        db,
        project_id,
        datum=payload.datum,
        document_id=payload.document_id,
        zusammenfassung=payload.zusammenfassung,
        teilnehmer_ids=payload.teilnehmer_ids,
    )


@router.get("/{meeting_id}", response_model=MeetingRead)
def get_meeting(project_id: int, meeting_id: int, db: Session = Depends(get_db)) -> MeetingRead:
    return meeting_service.get_meeting(db, project_id, meeting_id)


@router.patch("/{meeting_id}", response_model=MeetingRead)
def update_meeting(
    project_id: int, meeting_id: int, payload: MeetingUpdate, db: Session = Depends(get_db)
) -> MeetingRead:
    return meeting_service.update_meeting(db, project_id, meeting_id, payload)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(project_id: int, meeting_id: int, db: Session = Depends(get_db)) -> None:
    meeting_service.delete_meeting(db, project_id, meeting_id)


@router.post("/{meeting_id}/participants/{person_id}", response_model=MeetingRead)
def add_participant(
    project_id: int, meeting_id: int, person_id: int, db: Session = Depends(get_db)
) -> MeetingRead:
    return meeting_service.add_participant(db, project_id, meeting_id, person_id)


@router.delete("/{meeting_id}/participants/{person_id}", response_model=MeetingRead)
def remove_participant(
    project_id: int, meeting_id: int, person_id: int, db: Session = Depends(get_db)
) -> MeetingRead:
    return meeting_service.remove_participant(db, project_id, meeting_id, person_id)
