"""Duenne Kapselung um Microsoft Graph API + MSAL (siehe Briefing
Kernfunktion 12: Outlook-Ordnerueberwachung). Reine Funktionen ohne eigenen
Zustand, damit sie in Tests leicht durch Fakes ersetzt werden koennen (siehe
tests/conftest.py-Muster fuer den Claude-Client).

Bewusst KEIN Webhook/Push, sondern Filterung nach Empfangszeitpunkt statt
Delta-Query (beide laut Briefing zulaessig - diese Variante braucht keine
persistente Delta-Token-Verwaltung).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import html2text
import httpx
import msal

from app.config import Settings

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
SCOPES = ["https://graph.microsoft.com/Mail.Read", "offline_access"]


class GraphApiError(Exception):
    """Fasst OAuth-/Graph-Fehler in einer fuer EmailWatchConfig.letzter_fehler
    lesbaren Meldung zusammen - loest nie einen Absturz aus (siehe Briefing:
    ein Ausfall der Outlook-Anbindung darf die restliche App nicht lahmlegen,
    analog zum Claude-Ausfall-Prinzip).
    """


class GraphNotConfiguredError(GraphApiError):
    """MS_GRAPH_*-Variablen fehlen in der .env (siehe config.py)."""


@dataclass
class GraphTokens:
    access_token: str
    refresh_token: str
    expires_am: datetime


@dataclass
class GraphFolder:
    id: str
    name: str


@dataclass
class GraphMessage:
    id: str
    subject: str
    received_am: datetime
    sender: str
    plaintext_body: str


def _require_app_config(settings: Settings) -> tuple[str, str, str, str]:
    if not (
        settings.ms_graph_client_id
        and settings.ms_graph_client_secret
        and settings.ms_graph_tenant_id
        and settings.ms_graph_redirect_uri
    ):
        raise GraphNotConfiguredError(
            "Microsoft-Graph-App-Registrierung ist nicht vollstaendig konfiguriert "
            "(MS_GRAPH_CLIENT_ID/MS_GRAPH_CLIENT_SECRET/MS_GRAPH_TENANT_ID/"
            "MS_GRAPH_REDIRECT_URI in .env)."
        )
    return (
        settings.ms_graph_client_id,
        settings.ms_graph_client_secret,
        settings.ms_graph_tenant_id,
        settings.ms_graph_redirect_uri,
    )


def _confidential_client(settings: Settings) -> msal.ConfidentialClientApplication:
    client_id, client_secret, tenant_id, _ = _require_app_config(settings)
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    return msal.ConfidentialClientApplication(client_id, client_credential=client_secret, authority=authority)


def get_authorization_url(settings: Settings, state: str) -> str:
    _, _, _, redirect_uri = _require_app_config(settings)
    app = _confidential_client(settings)
    return app.get_authorization_request_url(SCOPES, state=state, redirect_uri=redirect_uri)


def exchange_code_for_tokens(settings: Settings, code: str) -> GraphTokens:
    _, _, _, redirect_uri = _require_app_config(settings)
    app = _confidential_client(settings)
    try:
        result = app.acquire_token_by_authorization_code(code, scopes=SCOPES, redirect_uri=redirect_uri)
    except Exception as exc:  # noqa: BLE001 - MSAL/Netzwerkfehler einheitlich uebersetzen
        raise GraphApiError(f"Microsoft-Login fehlgeschlagen: {exc}") from exc
    return _tokens_from_msal_result(result)


def refresh_tokens(settings: Settings, refresh_token: str) -> GraphTokens:
    app = _confidential_client(settings)
    try:
        result = app.acquire_token_by_refresh_token(refresh_token, scopes=SCOPES)
    except Exception as exc:  # noqa: BLE001
        raise GraphApiError(f"Token-Refresh fehlgeschlagen: {exc}") from exc
    return _tokens_from_msal_result(result, fallback_refresh_token=refresh_token)


def _tokens_from_msal_result(result: dict, *, fallback_refresh_token: str | None = None) -> GraphTokens:
    if "access_token" not in result:
        raise GraphApiError(
            result.get("error_description") or result.get("error") or "Microsoft-Login fehlgeschlagen."
        )
    # Microsoft rotiert Refresh-Tokens nicht immer - bei einem Refresh-Aufruf
    # faellt dieser Wert dann auf den bisherigen Refresh-Token zurueck.
    refresh_token = result.get("refresh_token") or fallback_refresh_token
    if not refresh_token:
        raise GraphApiError("Microsoft hat keinen Refresh-Token geliefert (offline_access-Scope pruefen).")
    expires_am = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=result.get("expires_in", 3600))
    return GraphTokens(access_token=result["access_token"], refresh_token=refresh_token, expires_am=expires_am)


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def get_account_email(access_token: str) -> str | None:
    try:
        response = httpx.get(f"{GRAPH_BASE_URL}/me", headers=_headers(access_token), timeout=15)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GraphApiError(f"Microsoft-Kontoinfo konnte nicht geladen werden: {exc}") from exc
    body = response.json()
    return body.get("mail") or body.get("userPrincipalName")


def list_mail_folders(access_token: str) -> list[GraphFolder]:
    try:
        response = httpx.get(
            f"{GRAPH_BASE_URL}/me/mailFolders",
            headers=_headers(access_token),
            params={"$top": 100, "$select": "id,displayName"},
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GraphApiError(f"Outlook-Ordner konnten nicht geladen werden: {exc}") from exc
    return [GraphFolder(id=item["id"], name=item["displayName"]) for item in response.json().get("value", [])]


def fetch_messages_since(access_token: str, folder_id: str, since: datetime | None) -> list[GraphMessage]:
    params: dict[str, str | int] = {
        "$select": "id,subject,receivedDateTime,from,body",
        "$orderby": "receivedDateTime asc",
        "$top": 100,
    }
    if since is not None:
        params["$filter"] = f"receivedDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}"

    try:
        response = httpx.get(
            f"{GRAPH_BASE_URL}/me/mailFolders/{folder_id}/messages",
            headers=_headers(access_token),
            params=params,
            timeout=30,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GraphApiError(f"Mails konnten nicht abgerufen werden: {exc}") from exc

    return [_parse_message(item) for item in response.json().get("value", [])]


def _parse_message(item: dict) -> GraphMessage:
    body = item.get("body") or {}
    content = body.get("content") or ""
    if body.get("contentType") == "html":
        content = _html_to_plaintext(content)
    sender = ((item.get("from") or {}).get("emailAddress") or {}).get("address", "")
    return GraphMessage(
        id=item["id"],
        subject=item.get("subject") or "",
        received_am=_parse_graph_datetime(item["receivedDateTime"]),
        sender=sender,
        plaintext_body=content.strip(),
    )


def _parse_graph_datetime(value: str) -> datetime:
    # Graph liefert z. B. "2026-08-15T10:30:00Z" oder mit Sekundenbruchteilen
    # ("...T10:30:00.1234567Z") - datetime.fromisoformat erlaubt maximal 6
    # Nachkommastellen, daher hier defensiv normalisiert statt strptime mit
    # starrem Format zu riskieren.
    trimmed = value.rstrip("Z")
    if "." in trimmed:
        date_part, frac = trimmed.split(".", 1)
        trimmed = f"{date_part}.{frac[:6]}"
    return datetime.fromisoformat(trimmed)


def _html_to_plaintext(html: str) -> str:
    converter = html2text.HTML2Text()
    converter.ignore_links = True
    converter.ignore_images = True
    converter.body_width = 0
    return converter.handle(html)
