from datetime import date, datetime

from sqlalchemy import Date, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.models.enums import DocumentStatus, DocumentType


class Document(Base):
    __tablename__ = "documents"
    # Duplikatserkennung ist projektspezifisch (siehe Briefing Punkt 2), daher
    # Index statt globaler Unique-Constraint - zwei Projekte duerfen dieselbe Datei
    # unabhaengig voneinander enthalten.
    __table_args__ = (UniqueConstraint("project_id", "datei_hash", name="uq_document_project_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    typ: Mapped[DocumentType] = mapped_column(SAEnum(DocumentType, native_enum=False, length=30), nullable=False)
    titel: Mapped[str] = mapped_column(String(300), nullable=False)

    # Bei Textdokumenten: extrahierter/eingegebener Originaltext.
    # Bei Bildern: die von mir bestaetigte, kanonische Retrieval-Fassung (siehe ki_analyse_rohtext/ocr_text).
    inhalt: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ki_analyse_rohtext: Mapped[str | None] = mapped_column(Text, nullable=True)

    original_dateipfad: Mapped[str | None] = mapped_column(String(500), nullable=True)
    datei_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    dateiname: Mapped[str | None] = mapped_column(String(300), nullable=True)

    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, native_enum=False, length=30),
        nullable=False,
        default=DocumentStatus.PENDING,
    )
    fehlermeldung: Mapped[str | None] = mapped_column(Text, nullable=True)

    dokumentdatum: Mapped[date | None] = mapped_column(Date, nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    aktualisiert_am: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Soft-Delete (technische Entscheidung, siehe Architekturuebersicht): getrennt vom
    # Ingestion-Status, damit `status` ausschliesslich die Pipeline beschreibt.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DocumentTag(Base):
    __tablename__ = "document_tags"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
