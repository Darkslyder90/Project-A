import shutil

from sqlalchemy.orm import Session

from app.api.schemas.project import ProjectUpdate
from app.config import get_settings
from app.core.exceptions import NotFoundError
from app.db.models.index_metadata import IndexMetadata
from app.db.models.project import Project
from app.indexing.chroma_client import get_chroma_client


def list_projects(db: Session) -> list[Project]:
    return list(db.query(Project).order_by(Project.name).all())


def get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"Projekt {project_id} wurde nicht gefunden.")
    return project


def create_project(db: Session, *, name: str, beschreibung: str | None) -> Project:
    project = Project(name=name, beschreibung=beschreibung)
    db.add(project)
    db.flush()  # damit project.id fuer IndexMetadata verfuegbar ist

    # Jedes Projekt bekommt sofort seine (noch leere) IndexMetadata-Zeile,
    # damit spaeterer Code nie mit einem fehlenden 1:1-Datensatz umgehen muss.
    db.add(IndexMetadata(project_id=project.id))

    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project_id: int, update: ProjectUpdate) -> Project:
    project = get_project(db, project_id)

    # model_fields_set statt "if wert is not None": beschreibung darf bewusst auf
    # None gesetzt werden ("Beschreibung loeschen"), das muss von "Feld war im
    # PATCH-Request gar nicht enthalten" unterscheidbar sein.
    for field in update.model_fields_set:
        setattr(project, field, getattr(update, field))

    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int) -> None:
    project = get_project(db, project_id)

    settings = get_settings()
    project_uploads_dir = settings.uploads_dir / str(project_id)

    # Collection-Name VOR dem Loeschen der Projekt-Zeile sichern - IndexMetadata
    # verschwindet gleich per FK-Kaskade zusammen mit dem Project.
    index_meta = db.get(IndexMetadata, project_id)
    collection_name = index_meta.active_collection_name if index_meta else None

    # DB-Loeschung zuerst: SQLite-FK-Kaskaden (ON DELETE CASCADE) raeumen alle
    # abhaengigen Zeilen (Documents, Chunks, Tags, Personen, Tasks, Meetings,
    # Chats, IndexMetadata, ApiUsageLogs) in derselben Transaktion aus.
    db.delete(project)
    db.commit()

    # Dateisystem/Chroma liegen ausserhalb der DB-Transaktion (siehe Briefing:
    # keine klassische Cross-Store-ACID-Transaktion moeglich) - danach
    # best-effort aufraeumen. Ein erneuter Aufruf ist gefahrlos (Verzeichnis
    # bzw. Collection existieren dann bereits nicht mehr).
    shutil.rmtree(project_uploads_dir, ignore_errors=True)

    if collection_name:
        client = get_chroma_client(str(settings.chroma_dir))
        try:
            client.delete_collection(collection_name)
        except Exception:  # noqa: BLE001 - Collection ggf. bereits weg, kein harter Fehler
            pass
