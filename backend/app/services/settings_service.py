from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.schemas.settings import AppSettingsUpdate, UsagePeriodSummary, UsageSummaryRead
from app.config import get_settings
from app.core.exceptions import ValidationAppError
from app.db.models.api_usage_log import ApiUsageLog
from app.db.models.app_settings import AppSettings
from app.security.crypto import EncryptionUnavailableError, decrypt, encrypt

_SINGLETON_ID = 1


def get_app_settings(db: Session) -> AppSettings:
    """Liefert die eine globale Settings-Zeile, legt sie mit Modell-Defaults an,
    falls sie noch nicht existiert (siehe AppSettings-Modell). Wird sowohl von
    der Settings-UI (Schritt 13) als auch von der Ingestion-Pipeline
    (Embedding-Modell, Chunk-Groesse) und dem Hybrid Retrieval (candidate_k/
    final_k) genutzt.
    """
    settings_row = db.get(AppSettings, _SINGLETON_ID)
    if settings_row is None:
        settings_row = AppSettings(id=_SINGLETON_ID)
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row


def _decrypt_stored_key(app_settings: AppSettings) -> str | None:
    if not app_settings.claude_api_key_encrypted:
        return None
    settings = get_settings()
    return decrypt(app_settings.claude_api_key_encrypted, settings.settings_encryption_key)


def get_api_key_status(db: Session) -> tuple[str, str | None]:
    """Ermittelt Status + maskierte Darstellung des effektiven Claude-API-Keys
    (siehe Briefing: DB-Key zuerst, .env-Key als Fallback, im UI nur maskiert
    z. B. 'sk-ant-...xxxx' anzeigen, Klartext nie).
    """
    app_settings = get_app_settings(db)

    if app_settings.claude_api_key_encrypted:
        plaintext = _decrypt_stored_key(app_settings)
        if plaintext is None:
            return "db_invalid", None
        return "db", _mask(plaintext)

    settings = get_settings()
    if settings.claude_api_key:
        return "env", _mask(settings.claude_api_key)

    return "none", None


def _mask(key: str) -> str:
    if len(key) <= 8:
        return "…" + key[-2:]
    return f"{key[:7]}…{key[-4:]}"


def resolve_effective_claude_api_key(db: Session) -> str | None:
    """DB-gespeicherter (entschluesselter) Key zuerst, sonst .env-Fallback
    (siehe Briefing Reihenfolge). Liefert None, wenn gar kein Key verfuegbar
    ist ODER ein gespeicherter Key nicht entschluesselt werden kann - der
    Aufrufer (claude_client) behandelt beides gleich als "Claude nicht
    verfuegbar", nicht als Absturz.
    """
    app_settings = get_app_settings(db)
    if app_settings.claude_api_key_encrypted:
        return _decrypt_stored_key(app_settings)

    return get_settings().claude_api_key


def resolve_effective_claude_model(db: Session) -> str:
    app_settings = get_app_settings(db)
    return app_settings.claude_model or get_settings().claude_model_default


def update_app_settings(db: Session, update: AppSettingsUpdate) -> AppSettings:
    app_settings = get_app_settings(db)
    fields = update.model_fields_set

    if "claude_api_key" in fields:
        if update.claude_api_key:
            try:
                app_settings.claude_api_key_encrypted = encrypt(
                    update.claude_api_key, get_settings().settings_encryption_key
                )
            except EncryptionUnavailableError as exc:
                raise ValidationAppError(str(exc)) from exc
        else:
            # Leerer String = gespeicherten Key bewusst entfernen (Fallback auf .env greift dann wieder).
            app_settings.claude_api_key_encrypted = None

    for field in fields - {"claude_api_key"}:
        setattr(app_settings, field, getattr(update, field))

    db.commit()
    db.refresh(app_settings)
    return app_settings


def get_usage_summary(db: Session) -> UsageSummaryRead:
    """Aggregiert ApiUsageLog fuer heute/diese Woche/diesen Monat (siehe
    Briefing: nur Kennzahlen, z. B. "Heute: 47 API-Aufrufe / 183k Tokens" -
    keine Kostenanzeige ohne gepflegte Preisparameter).
    """
    now = datetime.now(UTC).replace(tzinfo=None)  # erstellt_am ist naiv (UTC), siehe ApiUsageLog
    heute_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    woche_start = heute_start - timedelta(days=now.weekday())
    monat_start = heute_start.replace(day=1)

    def _summary(since: datetime) -> UsagePeriodSummary:
        row = (
            db.query(
                func.count(ApiUsageLog.id),
                func.coalesce(func.sum(ApiUsageLog.input_tokens + ApiUsageLog.output_tokens), 0),
            )
            .filter(ApiUsageLog.erstellt_am >= since)
            .one()
        )
        return UsagePeriodSummary(anfragen=row[0], tokens=int(row[1]))

    return UsageSummaryRead(
        heute=_summary(heute_start),
        woche=_summary(woche_start),
        monat=_summary(monat_start),
    )
