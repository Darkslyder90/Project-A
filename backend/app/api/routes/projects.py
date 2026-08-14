import shutil

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.deps import get_db, get_task_runner
from app.api.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.background.task_runner import DocumentTaskRunner
from app.config import get_settings
from app.core.exceptions import ValidationAppError
from app.services import export_service, import_service, project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return project_service.list_projects(db)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    return project_service.create_project(db, name=payload.name, beschreibung=payload.beschreibung)


# Statische Pfade ("/import") bewusst VOR den "/{project_id}"-Routen registriert,
# damit sie eindeutig unabhaengig von der Reihenfolge nie faelschlich als
# project_id="import" interpretiert werden (project_id ist typisiert als int,
# daher wuerde FastAPI "import" ohnehin nicht dorthin routen - Klarheit halber
# trotzdem vorangestellt).
@router.post("/import", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def import_project(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    task_runner: DocumentTaskRunner = Depends(get_task_runner),
) -> ProjectRead:
    content = await file.read()
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationAppError(
            f"Export-Datei ist zu gross ({len(content) / 1_048_576:.1f} MB). "
            f"Maximum: {settings.max_upload_size_mb} MB."
        )
    return import_service.import_project(db, task_runner, content)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)) -> ProjectRead:
    return project_service.get_project(db, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)) -> ProjectRead:
    return project_service.update_project(db, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)) -> None:
    project_service.delete_project(db, project_id)


@router.get("/{project_id}/export")
def export_project(project_id: int, db: Session = Depends(get_db)) -> FileResponse:
    zip_path = export_service.export_project(db, project_id)
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=zip_path.name,
        # Das temporaere Export-Verzeichnis wird erst entfernt, NACHDEM die
        # Response vollstaendig ausgeliefert wurde (Starlette BackgroundTask),
        # sonst waere die Datei beim Lesen ggf. schon wieder weg.
        background=BackgroundTask(shutil.rmtree, zip_path.parent, ignore_errors=True),
    )
