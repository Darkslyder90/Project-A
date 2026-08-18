from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailWatchConfig(Base):
    """Ein Datensatz pro Projekt (1:1, wie IndexMetadata) - Outlook-
    Ordnerueberwachung ist optional, nicht jedes Projekt hat zwingend eine
    Anbindung (siehe Briefing Kernfunktion 12). Bewusst OHNE die OAuth-Tokens
    selbst (siehe EmailOAuthAccount) - Token-Rotation soll nicht diese
    fachliche Konfiguration mitversionieren.
    """

    __tablename__ = "email_watch_configs"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )

    outlook_ordner_id: Mapped[str] = mapped_column(String(300), nullable=False)
    outlook_ordner_name: Mapped[str] = mapped_column(String(300), nullable=False)
    aktiv: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    polling_intervall_minuten: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    letzte_abfrage_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    letzter_fehler: Mapped[str | None] = mapped_column(Text, nullable=True)
