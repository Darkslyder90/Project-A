import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import ValidationAppError
from app.db.models.email_oauth_account import EmailOAuthAccount
from app.security.crypto import EncryptionUnavailableError, decrypt, encrypt
from app.services import ms_graph_client
from app.services.ms_graph_client import GraphApiError, GraphTokens

_SINGLETON_ID = 1
# Etwas Sicherheitsabstand vor dem tatsaechlichen Ablauf, damit ein Poll nie
# mitten in der Verarbeitung mit einem gerade abgelaufenen Token fehlschlaegt.
_REFRESH_MARGIN = timedelta(minutes=5)


def get_account(db: Session) -> EmailOAuthAccount:
    """Liefert die eine globale OAuth-Zeile (id=1, siehe Modell-Docstring),
    legt sie bei Bedarf leer an - analog zu settings_service.get_app_settings.
    """
    account = db.get(EmailOAuthAccount, _SINGLETON_ID)
    if account is None:
        account = EmailOAuthAccount(id=_SINGLETON_ID)
        db.add(account)
        db.commit()
        db.refresh(account)
    return account


def is_connected(db: Session) -> bool:
    return get_account(db).refresh_token_encrypted is not None


def start_login(db: Session) -> str:  # noqa: ARG001 - db-Parameter fuer einheitliche Service-Signatur
    """Liefert die Microsoft-Login-URL, an die der Browser weitergeleitet
    werden soll (siehe Settings-Route "Outlook-Ordnerueberwachung")."""
    settings = get_settings()
    state = uuid.uuid4().hex
    return ms_graph_client.get_authorization_url(settings, state)


def complete_login(db: Session, code: str) -> EmailOAuthAccount:
    """Tauscht den von Microsoft gelieferten Autorisierungscode gegen Tokens,
    verschluesselt sie und speichert sie (siehe _store_tokens)."""
    settings = get_settings()
    tokens = ms_graph_client.exchange_code_for_tokens(settings, code)
    account_email = ms_graph_client.get_account_email(tokens.access_token)
    return _store_tokens(db, tokens, account_email=account_email)


def disconnect(db: Session) -> None:
    account = get_account(db)
    account.access_token_encrypted = None
    account.refresh_token_encrypted = None
    account.access_token_expires_am = None
    account.account_email = None
    account.verbunden_am = None
    db.commit()


def get_valid_access_token(db: Session) -> str:
    """Liefert einen gueltigen Access-Token, erneuert bei Bedarf automatisch
    ueber den Refresh-Token (siehe Briefing: "Token-Refresh laeuft automatisch
    im Hintergrund vor Ablauf"). Wirft GraphApiError statt abzustuerzen, wenn
    (noch) kein Konto verbunden ist oder die Entschluesselung fehlschlaegt -
    der Aufrufer (email_watch_service) behandelt das als Poll-Fehler.
    """
    account = get_account(db)
    if not account.refresh_token_encrypted:
        raise GraphApiError("Kein Microsoft-Konto verbunden - erst in den Settings anmelden.")

    secret = get_settings().settings_encryption_key
    refresh_token = decrypt(account.refresh_token_encrypted, secret)
    if refresh_token is None:
        raise GraphApiError("Gespeicherte Microsoft-Tokens koennen nicht entschluesselt werden - erneut anmelden.")

    now = datetime.now(UTC).replace(tzinfo=None)
    needs_refresh = (
        account.access_token_encrypted is None
        or account.access_token_expires_am is None
        or account.access_token_expires_am - now < _REFRESH_MARGIN
    )
    if not needs_refresh:
        access_token = decrypt(account.access_token_encrypted, secret)
        if access_token is not None:
            return access_token

    tokens = ms_graph_client.refresh_tokens(get_settings(), refresh_token)
    _store_tokens(db, tokens)
    return tokens.access_token


def _store_tokens(db: Session, tokens: GraphTokens, *, account_email: str | None = None) -> EmailOAuthAccount:
    account = get_account(db)
    secret = get_settings().settings_encryption_key
    try:
        account.access_token_encrypted = encrypt(tokens.access_token, secret)
        account.refresh_token_encrypted = encrypt(tokens.refresh_token, secret)
    except EncryptionUnavailableError as exc:
        raise ValidationAppError(str(exc)) from exc
    account.access_token_expires_am = tokens.expires_am
    if account_email:
        account.account_email = account_email
    if account.verbunden_am is None:
        account.verbunden_am = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(account)
    return account
