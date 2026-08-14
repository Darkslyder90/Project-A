import time
from dataclasses import dataclass

import anthropic
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models.api_usage_log import ApiUsageLog
from app.db.models.enums import ApiUsagePurpose
from app.services.settings_service import resolve_effective_claude_api_key, resolve_effective_claude_model

DEFAULT_MAX_TOKENS = 4096


class ClaudeUnavailableError(AppError):
    """Claude ist nicht erreichbar/konfiguriert - darf laut Briefing nie die
    gesamte App lahmlegen, nur die tatsaechlich Claude benoetigenden Features
    (Chat, KI-Analyse). status_code=503 statt 500, damit das Frontend das als
    "vorübergehend nicht verfügbar" statt als Serverfehler behandeln kann.
    """

    status_code = 503


@dataclass
class ClaudeCallResult:
    text: str
    stop_reason: str
    model: str


def _resolve_api_key(db: Session) -> str:
    """Reihenfolge wie im Briefing beschrieben: verschluesselter DB-Key
    (Settings-UI, Schritt 13) zuerst, sonst optionaler .env-Fallback-Key.
    Ein gespeicherter Key, der nicht entschluesselt werden kann (fehlendes/
    geaendertes SETTINGS_ENCRYPTION_KEY), zaehlt wie "kein Key vorhanden" -
    verstaendliche Fehlermeldung statt Absturz.
    """
    api_key = resolve_effective_claude_api_key(db)
    if not api_key:
        raise ClaudeUnavailableError(
            "Kein Claude-API-Key konfiguriert (oder der gespeicherte Key kann nicht "
            "entschluesselt werden). Bitte in den Einstellungen einen Key hinterlegen "
            "oder CLAUDE_API_KEY in der .env setzen."
        )
    return api_key


def call_claude(
    db: Session,
    *,
    project_id: int | None,
    system: str,
    messages: list[dict],
    zweck: ApiUsagePurpose,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> ClaudeCallResult:
    """Einziger Ort, an dem die Anthropic-SDK aufgerufen wird. Protokolliert
    jeden Aufruf in ApiUsageLog (nur Kennzahlen, niemals Prompt-/Antworttext,
    siehe Briefing Datenschutz-Prinzip) und wandelt SDK-Fehler in eine saubere
    ClaudeUnavailableError um, statt die App abstuerzen zu lassen.
    """
    api_key = _resolve_api_key(db)
    client = anthropic.Anthropic(api_key=api_key)
    model = resolve_effective_claude_model(db)

    start = time.monotonic()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
    except anthropic.AuthenticationError as exc:
        _log_usage(db, project_id, zweck, model, 0, 0, start, False, "authentication_error")
        raise ClaudeUnavailableError("Claude-API-Key ist ungueltig.") from exc
    except anthropic.RateLimitError as exc:
        _log_usage(db, project_id, zweck, model, 0, 0, start, False, "rate_limit_error")
        raise ClaudeUnavailableError(
            "Claude-API ist aktuell ausgelastet, bitte spaeter erneut versuchen."
        ) from exc
    except anthropic.APIConnectionError as exc:
        _log_usage(db, project_id, zweck, model, 0, 0, start, False, "connection_error")
        raise ClaudeUnavailableError("Claude-API ist aktuell nicht erreichbar.") from exc
    except anthropic.APIStatusError as exc:
        _log_usage(db, project_id, zweck, model, 0, 0, start, False, str(exc.status_code))
        raise ClaudeUnavailableError(f"Claude-API-Fehler ({exc.status_code}).") from exc

    if response.stop_reason == "refusal":
        _log_usage(
            db, project_id, zweck, model,
            response.usage.input_tokens, response.usage.output_tokens,
            start, False, "refusal",
        )
        return ClaudeCallResult(text="", stop_reason="refusal", model=response.model)

    text = "".join(block.text for block in response.content if block.type == "text")
    _log_usage(
        db, project_id, zweck, model,
        response.usage.input_tokens, response.usage.output_tokens,
        start, True, None,
    )
    return ClaudeCallResult(text=text, stop_reason=response.stop_reason, model=response.model)


def _log_usage(
    db: Session,
    project_id: int | None,
    zweck: ApiUsagePurpose,
    model: str,
    input_tokens: int,
    output_tokens: int,
    start: float,
    erfolg: bool,
    fehlertyp: str | None,
) -> None:
    dauer_ms = int((time.monotonic() - start) * 1000)
    db.add(
        ApiUsageLog(
            project_id=project_id,
            zweck=zweck,
            modell=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            dauer_ms=dauer_ms,
            erfolg=erfolg,
            fehlertyp=fehlertyp,
        )
    )
    db.commit()
