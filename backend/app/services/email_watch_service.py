from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.background.task_runner import DocumentTaskRunner
from app.core.exceptions import NotFoundError
from app.db.models.email_watch_config import EmailWatchConfig
from app.db.models.enums import DocumentType
from app.services import document_service, email_oauth_service, ms_graph_client
from app.services.ms_graph_client import GraphApiError
from app.services.project_service import get_project

# Siehe Briefing Kernfunktion 12, "Zeitliche Begrenzung": Mails aelter als
# 1 Woche werden nie abgeholt, weder beim ersten Poll nach dem Einrichten
# noch bei einer verzoegerten/nachgeholten Abfrage.
_MAX_MAIL_AGE = timedelta(days=7)


def get_config(db: Session, project_id: int) -> EmailWatchConfig | None:
    get_project(db, project_id)  # 404, falls Projekt nicht existiert
    return db.get(EmailWatchConfig, project_id)


def upsert_config(
    db: Session,
    project_id: int,
    *,
    outlook_ordner_id: str,
    outlook_ordner_name: str,
    aktiv: bool,
    polling_intervall_minuten: int,
) -> EmailWatchConfig:
    get_project(db, project_id)
    config = db.get(EmailWatchConfig, project_id)
    if config is None:
        config = EmailWatchConfig(project_id=project_id)
        db.add(config)
    config.outlook_ordner_id = outlook_ordner_id
    config.outlook_ordner_name = outlook_ordner_name
    config.aktiv = aktiv
    config.polling_intervall_minuten = polling_intervall_minuten
    db.commit()
    db.refresh(config)
    return config


def delete_config(db: Session, project_id: int) -> None:
    get_project(db, project_id)
    config = db.get(EmailWatchConfig, project_id)
    if config is not None:
        db.delete(config)
        db.commit()


def poll_due_configs(db: Session, task_runner: DocumentTaskRunner) -> None:
    """Wird periodisch vom Scheduler aufgerufen (siehe
    background/email_scheduler.py) - prueft alle aktiven Konfigurationen und
    pollt nur die, deren eigenes Intervall seit der letzten Abfrage
    abgelaufen ist. Keine dynamische Job-Verwaltung pro Projekt noetig.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    configs = db.query(EmailWatchConfig).filter(EmailWatchConfig.aktiv.is_(True)).all()
    for config in configs:
        due = config.letzte_abfrage_am is None or (
            now - config.letzte_abfrage_am >= timedelta(minutes=config.polling_intervall_minuten)
        )
        if due:
            poll_one(db, config, task_runner)


def poll_now(db: Session, project_id: int, task_runner: DocumentTaskRunner) -> EmailWatchConfig:
    """Manueller Sofort-Poll (Settings-Button), unabhaengig vom eigenen
    Intervall des Projekts."""
    get_project(db, project_id)
    config = db.get(EmailWatchConfig, project_id)
    if config is None:
        raise NotFoundError(f"Projekt {project_id} hat keine Outlook-Ordnerueberwachung konfiguriert.")
    poll_one(db, config, task_runner)
    return config


def poll_one(db: Session, config: EmailWatchConfig, task_runner: DocumentTaskRunner) -> None:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - _MAX_MAIL_AGE
    # since ist nie None und nie aelter als der Cutoff - sonst wuerde der
    # allererste Poll (letzte_abfrage_am is None) serverseitig ungefiltert
    # nach "aeltestes zuerst" abfragen und bei einem gut gefuellten Postfach
    # nie bei den tatsaechlich relevanten, juengeren Mails ankommen.
    since = config.letzte_abfrage_am
    if since is None or since < cutoff:
        since = cutoff

    try:
        access_token = email_oauth_service.get_valid_access_token(db)
        messages = ms_graph_client.fetch_messages_since(access_token, config.outlook_ordner_id, since)
    except GraphApiError as exc:
        config.letzter_fehler = str(exc)
        db.commit()
        return

    for message in messages:
        if message.received_am < cutoff:
            continue  # defensiv - serverseitiger Filter oben deckt das bereits ab
        if document_service.find_document_by_outlook_message_id(db, config.project_id, message.id):
            continue

        absender_betreff = f"{message.sender}: {message.subject}".strip(": ")
        document_service.create_manual_document(
            db,
            config.project_id,
            typ=DocumentType.EMAIL,
            titel=message.subject or "(kein Betreff)",
            inhalt=message.plaintext_body,
            dokumentdatum=message.received_am.date(),
            task_runner=task_runner,
            dateiname=absender_betreff or None,
            outlook_message_id=message.id,
        )

    config.letzter_fehler = None
    config.letzte_abfrage_am = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
