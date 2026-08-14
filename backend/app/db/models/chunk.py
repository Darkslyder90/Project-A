from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Chunk(Base):
    """Abgeleiteter Indexdatensatz (siehe Source-of-Truth-Prinzip im Briefing) -
    jederzeit vollstaendig aus Document + Originaldatei rekonstruierbar.

    id ist bewusst ein String (UUID4-Hex), nicht Autoincrement-Integer: das Briefing
    verlangt, dass chunk_id identisch mit der ID des zugehoerigen Chroma-Eintrags ist,
    und Chroma-IDs sind Strings.
    """

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "index_version", "chunk_index", name="uq_chunk_document_version_index"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    index_version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    seite: Mapped[int | None] = mapped_column(Integer, nullable=True)
    abschnitt: Mapped[str | None] = mapped_column(String(300), nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Denormalisiert fuer schnellen Zugriff bei Quellenangaben (siehe Briefing).
    dateiname: Mapped[str | None] = mapped_column(String(300), nullable=True)
    dokumenttyp: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dokumentdatum: Mapped[date | None] = mapped_column(Date, nullable=True)
    meeting_datum: Mapped[date | None] = mapped_column(Date, nullable=True)
    meeting_teilnehmer: Mapped[str | None] = mapped_column(Text, nullable=True)
