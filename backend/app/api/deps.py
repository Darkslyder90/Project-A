from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.background.task_runner import DocumentTaskRunner


def get_db(request: Request) -> Generator[Session, None, None]:
    """DB-Session-Dependency. Liest die Session-Factory aus app.state statt aus
    einem Modul-globalen Singleton (siehe db/session.py) - dadurch kann jede
    FastAPI-App-Instanz (Prod, Dev, Tests) ihre eigene, isolierte Engine haben.
    """
    session_factory = request.app.state.session_factory
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_task_runner(request: Request) -> DocumentTaskRunner:
    """Liefert den Background-Task-Runner der aktuellen App-Instanz (siehe
    app.state in main.py) - analog zu get_db, damit jede App-Instanz
    (Prod/Dev/Tests) ihren eigenen, isolierten Runner hat.
    """
    return request.app.state.task_runner
