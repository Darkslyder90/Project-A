from datetime import date

from sqlalchemy.orm import Session

from app.api.schemas.task import TaskUpdate
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.models.enums import TaskStatus
from app.db.models.person import Person
from app.db.models.task import Task, TaskDocument
from app.services.document_service import get_document
from app.services.project_service import get_project


def _validate_person_in_project(db: Session, project_id: int, person_id: int | None) -> None:
    if person_id is None:
        return
    person = db.query(Person).filter(Person.id == person_id, Person.project_id == project_id).first()
    if person is None:
        raise ValidationAppError(f"Person {person_id} gehoert nicht zu Projekt {project_id}.")


def list_tasks(db: Session, project_id: int, status_filter: TaskStatus | None = None) -> list[Task]:
    get_project(db, project_id)  # 404, falls Projekt nicht existiert
    query = db.query(Task).filter(Task.project_id == project_id)
    if status_filter is not None:
        query = query.filter(Task.status == status_filter)
    # Faellige Tasks zuerst (nach Datum), Tasks ohne Faelligkeitsdatum zuletzt.
    return query.order_by(Task.faellig_am.is_(None), Task.faellig_am).all()


def get_task(db: Session, project_id: int, task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if task is None:
        raise NotFoundError(f"Task {task_id} wurde in Projekt {project_id} nicht gefunden.")
    return task


def create_task(
    db: Session,
    project_id: int,
    *,
    titel: str,
    beschreibung: str | None,
    status: TaskStatus,
    zugewiesen_an: int | None,
    faellig_am: date | None,
    dokument_ids: list[int],
) -> Task:
    get_project(db, project_id)
    _validate_person_in_project(db, project_id, zugewiesen_an)
    for document_id in dokument_ids:
        get_document(db, project_id, document_id)  # 404 + Projektgrenze pruefen

    task = Task(
        project_id=project_id,
        titel=titel,
        beschreibung=beschreibung,
        status=status,
        zugewiesen_an=zugewiesen_an,
        faellig_am=faellig_am,
    )
    db.add(task)
    db.flush()  # task.id fuer die TaskDocument-Zeilen verfuegbar machen

    for document_id in set(dokument_ids):
        db.add(TaskDocument(task_id=task.id, document_id=document_id))

    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, project_id: int, task_id: int, update: TaskUpdate) -> Task:
    task = get_task(db, project_id, task_id)

    if "zugewiesen_an" in update.model_fields_set:
        _validate_person_in_project(db, project_id, update.zugewiesen_an)

    for field in update.model_fields_set:
        setattr(task, field, getattr(update, field))

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, project_id: int, task_id: int) -> None:
    task = get_task(db, project_id, task_id)
    db.delete(task)  # TaskDocument-Zeilen raeumt die FK-Kaskade mit auf
    db.commit()


def link_document(db: Session, project_id: int, task_id: int, document_id: int) -> Task:
    task = get_task(db, project_id, task_id)
    get_document(db, project_id, document_id)  # 404 + Projektgrenze pruefen

    existing = db.get(TaskDocument, (task_id, document_id))
    if existing is None:
        db.add(TaskDocument(task_id=task_id, document_id=document_id))
        db.commit()
        db.refresh(task)
    return task


def unlink_document(db: Session, project_id: int, task_id: int, document_id: int) -> Task:
    task = get_task(db, project_id, task_id)

    link = db.get(TaskDocument, (task_id, document_id))
    if link is not None:
        db.delete(link)
        db.commit()
        db.refresh(task)
    return task
