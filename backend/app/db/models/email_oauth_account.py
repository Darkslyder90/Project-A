from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailOAuthAccount(Base):
    """Genau eine Zeile (id=1, wie AppSettings) - ein Microsoft-Konto pro
    Project-A-Instanz, ueber das mehrere Projekte jeweils einen eigenen
    Outlook-Ordner ueberwachen koennen (siehe EmailWatchConfig, Briefing
    Kernfunktion 12). Getrennt von EmailWatchConfig, damit ein Token-Refresh
    nicht die fachliche Ordner-Konfiguration eines Projekts mitversioniert.

    Technische Entscheidung (Briefing erlaubt explizit ein eigenes Secret):
    Tokens werden mit demselben Fernet-Mechanismus wie der Claude-API-Key
    verschluesselt (app.security.crypto, siehe settings_service), unter
    Wiederverwendung von SETTINGS_ENCRYPTION_KEY statt eines zweiten Secrets -
    weniger operative Komplexitaet fuer eine Single-User-App mit ohnehin nur
    einem Secret-Backup-Vorgang.
    """

    __tablename__ = "email_oauth_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)

    account_email: Mapped[str | None] = mapped_column(String(300), nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_expires_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verbunden_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
