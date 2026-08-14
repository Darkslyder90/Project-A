from sqlalchemy.orm import Session

from app.api.schemas.person import PersonUpdate
from app.core.exceptions import NotFoundError
from app.db.models.person import Person
from app.services.project_service import get_project


def list_people(db: Session, project_id: int) -> list[Person]:
    get_project(db, project_id)  # 404, falls Projekt nicht existiert
    return db.query(Person).filter(Person.project_id == project_id).order_by(Person.name).all()


def get_person(db: Session, project_id: int, person_id: int) -> Person:
    person = (
        db.query(Person).filter(Person.id == person_id, Person.project_id == project_id).first()
    )
    if person is None:
        raise NotFoundError(f"Person {person_id} wurde in Projekt {project_id} nicht gefunden.")
    return person


def create_person(
    db: Session,
    project_id: int,
    *,
    name: str,
    rolle: str | None,
    kontaktinfo: str | None,
    notizen: str | None,
) -> Person:
    get_project(db, project_id)

    person = Person(project_id=project_id, name=name, rolle=rolle, kontaktinfo=kontaktinfo, notizen=notizen)
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def update_person(db: Session, project_id: int, person_id: int, update: PersonUpdate) -> Person:
    person = get_person(db, project_id, person_id)

    for field in update.model_fields_set:
        setattr(person, field, getattr(update, field))

    db.commit()
    db.refresh(person)
    return person


def delete_person(db: Session, project_id: int, person_id: int) -> None:
    """Siehe Briefing: Tasks bleiben bestehen (zugewiesen_an -> NULL),
    MeetingParticipant-Verknuepfungen werden entfernt, keine Tasks/Meetings
    werden automatisch mitgeloescht. Beides ist bereits ueber
    ON DELETE SET NULL (Task.zugewiesen_an) bzw. ON DELETE CASCADE
    (MeetingParticipant.person_id) auf DB-Ebene abgedeckt (PRAGMA
    foreign_keys=ON) - hier reicht das einfache Loeschen der Person-Zeile.
    """
    person = get_person(db, project_id, person_id)
    db.delete(person)
    db.commit()
