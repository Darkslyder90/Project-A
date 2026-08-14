from datetime import datetime

from sqlalchemy import JSON, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.models.enums import ChatRole


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    titel: Mapped[str | None] = mapped_column(String(300), nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    zuletzt_aktualisiert_am: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rolle: Mapped[ChatRole] = mapped_column(SAEnum(ChatRole, native_enum=False, length=20), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Quellen-Snapshot (siehe Briefing): damalige Metadaten, unabhaengig vom aktuellen
    # Zustand des referenzierten Documents. Liste von Objekten mit u. a. document_id
    # (falls das Dokument noch existiert), Titel, Datum, Seite/Abschnitt, Textausschnitt.
    quellen: Mapped[list | None] = mapped_column(JSON, nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
