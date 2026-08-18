from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_task_runner
from app.api.schemas.email_watch import (
    EmailWatchConfigRead,
    EmailWatchConfigUpdate,
    MailFolderRead,
    OAuthLoginUrlRead,
    OAuthStatusRead,
)
from app.background.task_runner import DocumentTaskRunner
from app.core.exceptions import ValidationAppError
from app.services import email_oauth_service, email_watch_service, ms_graph_client
from app.services.ms_graph_client import GraphApiError

# Zwei Geltungsbereiche in einer Datei: das Microsoft-Konto/OAuth ist global
# (ein Konto pro Project-A-Instanz, siehe EmailOAuthAccount-Modell-Docstring),
# die eigentliche Ordner-Zuordnung (EmailWatchConfig) ist pro Projekt - kein
# gemeinsamer Prefix moeglich, daher volle Pfade pro Route.
router = APIRouter(tags=["email-watch"])


@router.get("/api/email-watch/oauth/login", response_model=OAuthLoginUrlRead)
def oauth_login(db: Session = Depends(get_db)) -> OAuthLoginUrlRead:
    try:
        url = email_oauth_service.start_login(db)
    except GraphApiError as exc:
        raise ValidationAppError(str(exc)) from exc
    return OAuthLoginUrlRead(authorization_url=url)


@router.get("/api/email-watch/oauth/callback")
def oauth_callback(
    code: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Ziel des Microsoft-Redirects nach dem Login (siehe MS_GRAPH_REDIRECT_URI)
    - leitet den Browser danach zurueck in die Settings-Seite des Frontends,
    mit einem Query-Flag statt einer rohen JSON-Antwort (Browser-Redirect-Flow,
    kein API-Aufruf durch den Client selbst).
    """
    if error or not code:
        return RedirectResponse(url="/settings?outlook_oauth=error")
    try:
        email_oauth_service.complete_login(db, code)
    except GraphApiError:
        return RedirectResponse(url="/settings?outlook_oauth=error")
    return RedirectResponse(url="/settings?outlook_oauth=success")


@router.get("/api/email-watch/oauth/status", response_model=OAuthStatusRead)
def oauth_status(db: Session = Depends(get_db)) -> OAuthStatusRead:
    account = email_oauth_service.get_account(db)
    return OAuthStatusRead(
        connected=account.refresh_token_encrypted is not None,
        account_email=account.account_email,
        access_token_expires_am=account.access_token_expires_am,
    )


@router.post("/api/email-watch/oauth/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def oauth_disconnect(db: Session = Depends(get_db)) -> None:
    email_oauth_service.disconnect(db)


@router.get("/api/email-watch/folders", response_model=list[MailFolderRead])
def list_folders(db: Session = Depends(get_db)) -> list[MailFolderRead]:
    try:
        access_token = email_oauth_service.get_valid_access_token(db)
        folders = ms_graph_client.list_mail_folders(access_token)
    except GraphApiError as exc:
        raise ValidationAppError(str(exc)) from exc
    return [MailFolderRead(id=folder.id, name=folder.name) for folder in folders]


@router.get("/api/projects/{project_id}/email-watch-config", response_model=EmailWatchConfigRead | None)
def get_config(project_id: int, db: Session = Depends(get_db)) -> EmailWatchConfigRead | None:
    return email_watch_service.get_config(db, project_id)


@router.put("/api/projects/{project_id}/email-watch-config", response_model=EmailWatchConfigRead)
def upsert_config(
    project_id: int, payload: EmailWatchConfigUpdate, db: Session = Depends(get_db)
) -> EmailWatchConfigRead:
    return email_watch_service.upsert_config(
        db,
        project_id,
        outlook_ordner_id=payload.outlook_ordner_id,
        outlook_ordner_name=payload.outlook_ordner_name,
        aktiv=payload.aktiv,
        polling_intervall_minuten=payload.polling_intervall_minuten,
    )


@router.delete("/api/projects/{project_id}/email-watch-config", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(project_id: int, db: Session = Depends(get_db)) -> None:
    email_watch_service.delete_config(db, project_id)


@router.post("/api/projects/{project_id}/email-watch-config/poll-now", response_model=EmailWatchConfigRead)
def poll_now(
    project_id: int,
    db: Session = Depends(get_db),
    task_runner: DocumentTaskRunner = Depends(get_task_runner),
) -> EmailWatchConfigRead:
    return email_watch_service.poll_now(db, project_id, task_runner)
