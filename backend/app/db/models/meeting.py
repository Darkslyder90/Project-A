from datetime import date

from sqlalchemy import Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    datum: Mapped[date] = mapped_column(Date, nullable=False)
    # Pflichtbezug auf genau ein Document (Source of Truth fuer den Transkripttext).
    # Bewusst OHNE ondelete=CASCADE: ein Document, das ein Meeting traegt, darf laut
    # Briefing nicht separat geloescht werden - SQLite blockiert das auf DB-Ebene
    # (PRAGMA foreign_keys=ON), der Service gibt vorher eine verstaendliche Fehlermeldung.
    # unique=True erzwingt die 1:1-Beziehung (ein Document ist hoechstens eines Meetings Transkript).
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), nullable=False, unique=True, index=True
    )
    zusammenfassung: Mapped[str | None] = mapped_column(Text, nullable=True)


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), primary_key=True)
