import os

from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends

from app.api.deps import get_db
from app.config import get_settings

router = APIRouter()


@router.get("/health")
def health(response: Response, db: Session = Depends(get_db)) -> dict:
    """Prueft NUR lokale Voraussetzungen (FastAPI laeuft, SQLite erreichbar,
    persistente Verzeichnisse zugreifbar). Loest bewusst KEINEN Claude-API-Aufruf
    aus (siehe Briefing: Kosten/Zuverlaessigkeit des Healthchecks).
    """
    settings = get_settings()
    checks: dict[str, str] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - Healthcheck soll nie 500en
        checks["database"] = f"error: {exc.__class__.__name__}"

    for name, path in (
        ("data_dir", settings.data_dir),
        ("uploads_dir", settings.uploads_dir),
        ("chroma_dir", settings.chroma_dir),
        ("backups_dir", settings.backups_dir),
    ):
        try:
            checks[name] = "ok" if path.is_dir() and os.access(path, os.W_OK) else "error: not writable"
        except OSError as exc:
            checks[name] = f"error: {exc.__class__.__name__}"

    healthy = all(v == "ok" for v in checks.values())
    if not healthy:
        response.status_code = 503

    return {"status": "ok" if healthy else "degraded", "checks": checks}
