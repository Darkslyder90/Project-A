from datetime import date

from sqlalchemy import Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    datum: Mapped[date] = mapped_column(Date, nullable=False)
    # Optionaler Bezug auf genau ein Document (Source of Truth fuer den
    # Transkripttext, sofern eines erfasst wurde - Korrektur: abweichend vom
    # urspruenglichen Briefing-Vorschlag "Pflichtbezug" auf ausdruecklichen
    # Nutzerwunsch nullable, ein Meeting kann auch ohne Protokoll angelegt
    # werden). Bewusst OHNE ondelete=CASCADE: ein Document, das ein Meeting
    # traegt, darf laut Briefing nicht separat geloescht werden - SQLite
    # blockiert das auf DB-Ebene (PRAGMA foreign_keys=ON), der Service gibt
    # vorher eine verstaendliche Fehlermeldung. unique=True erzwingt weiterhin
    # die 1:1-Beziehung, sofern ein Document gesetzt ist (SQLite erlaubt
    # mehrere NULLs in einer UNIQUE-Spalte).
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True, unique=True, index=True
    )
    zusammenfassung: Mapped[str | None] = mapped_column(Text, nullable=True)

    # viewonly: Pflege laeuft ueber meeting_service.add_participant/remove_participant
    # (explizite MeetingParticipant-Zeilen), diese Relationship dient nur der
    # bequemen Auswertung beim Lesen (siehe Meeting.teilnehmer_ids).
    participants: Mapped[list["Person"]] = relationship(  # noqa: F821
        secondary="meeting_participants", viewonly=True, order_by="Person.name"
    )

    @property
    def teilnehmer_ids(self) -> list[int]:
        return [p.id for p in self.participants]


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), primary_key=True)
