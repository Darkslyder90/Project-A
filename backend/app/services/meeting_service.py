from datetime import date

from sqlalchemy.orm import Session

from app.api.schemas.meeting import MeetingUpdate
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.db.models.meeting import Meeting, MeetingParticipant
from app.db.models.person import Person
from app.services import document_service
from app.services.project_service import get_project


def _validate_person_in_project(db: Session, project_id: int, person_id: int) -> None:
    person = db.query(Person).filter(Person.id == person_id, Person.project_id == project_id).first()
    if person is None:
        raise ValidationAppError(f"Person {person_id} gehoert nicht zu Projekt {project_id}.")


def _validate_document_for_meeting(
    db: Session, project_id: int, document_id: int, *, exclude_meeting_id: int | None = None
) -> None:
    document_service.get_document(db, project_id, document_id)  # 404 + Projektgrenze pruefen

    # Proaktiv statt den DB-Unique-Constraint als rohen IntegrityError durchschlagen
    # zu lassen (siehe Briefing: 1:1-Beziehung Meeting<->Document, sofern gesetzt).
    query = db.query(Meeting).filter(Meeting.document_id == document_id)
    if exclude_meeting_id is not None:
        query = query.filter(Meeting.id != exclude_meeting_id)
    existing = query.first()
    if existing is not None:
        raise ConflictError(
            f"Document {document_id} ist bereits das Protokoll von Meeting {existing.id}."
        )


def list_meetings(db: Session, project_id: int) -> list[Meeting]:
    get_project(db, project_id)  # 404, falls Projekt nicht existiert
    return (
        db.query(Meeting).filter(Meeting.project_id == project_id).order_by(Meeting.datum.desc()).all()
    )


def get_meeting(db: Session, project_id: int, meeting_id: int) -> Meeting:
    meeting = (
        db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.project_id == project_id).first()
    )
    if meeting is None:
        raise NotFoundError(f"Meeting {meeting_id} wurde in Projekt {project_id} nicht gefunden.")
    return meeting


def create_meeting(
    db: Session,
    project_id: int,
    *,
    datum: date,
    document_id: int | None,
    zusammenfassung: str | None,
    teilnehmer_ids: list[int],
) -> Meeting:
    get_project(db, project_id)
    if document_id is not None:
        _validate_document_for_meeting(db, project_id, document_id)

    for person_id in teilnehmer_ids:
        _validate_person_in_project(db, project_id, person_id)

    meeting = Meeting(
        project_id=project_id, datum=datum, document_id=document_id, zusammenfassung=zusammenfassung
    )
    db.add(meeting)
    db.flush()  # meeting.id fuer die MeetingParticipant-Zeilen verfuegbar machen

    for person_id in set(teilnehmer_ids):
        db.add(MeetingParticipant(meeting_id=meeting.id, person_id=person_id))

    db.commit()
    db.refresh(meeting)
    return meeting


def update_meeting(db: Session, project_id: int, meeting_id: int, update: MeetingUpdate) -> Meeting:
    meeting = get_meeting(db, project_id, meeting_id)

    if "document_id" in update.model_fields_set and update.document_id is not None:
        _validate_document_for_meeting(
            db, project_id, update.document_id, exclude_meeting_id=meeting_id
        )

    for field in update.model_fields_set:
        setattr(meeting, field, getattr(update, field))

    db.commit()
    db.refresh(meeting)
    return meeting


def delete_meeting(db: Session, project_id: int, meeting_id: int) -> None:
    """Loescht das Meeting. Hat es ein Protokoll-Dokument, wird das im selben
    Vorgang mitentfernt (siehe Briefing: das Document hat ohne das Meeting
    keine eigenstaendige fachliche Bedeutung mehr und bliebe sonst als Waise
    zurueck). Die Meeting-Zeile muss zuerst weg sein, da
    document_service.delete_document() eine Loeschung sonst wegen genau dieses
    Meeting-Bezugs blockieren wuerde.
    """
    meeting = get_meeting(db, project_id, meeting_id)
    document_id = meeting.document_id

    db.delete(meeting)
    db.commit()

    if document_id is not None:
        document_service.delete_document(db, project_id, document_id)


def add_participant(db: Session, project_id: int, meeting_id: int, person_id: int) -> Meeting:
    meeting = get_meeting(db, project_id, meeting_id)
    _validate_person_in_project(db, project_id, person_id)

    existing = db.get(MeetingParticipant, (meeting_id, person_id))
    if existing is None:
        db.add(MeetingParticipant(meeting_id=meeting_id, person_id=person_id))
        db.commit()
        db.refresh(meeting)
    return meeting


def remove_participant(db: Session, project_id: int, meeting_id: int, person_id: int) -> Meeting:
    meeting = get_meeting(db, project_id, meeting_id)

    link = db.get(MeetingParticipant, (meeting_id, person_id))
    if link is not None:
        db.delete(link)
        db.commit()
        db.refresh(meeting)
    return meeting
