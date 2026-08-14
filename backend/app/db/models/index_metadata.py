from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import RebuildStatus


class IndexMetadata(Base):
    """Ein Datensatz pro Projekt (1:1), haelt aktiven Index UND einen ggf. parallel
    im Aufbau befindlichen Index (Blue/Green-Rebuild) klar getrennt auseinander.
    """

    __tablename__ = "index_metadata"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )

    # Aktiver Index (das, was Retrieval tatsaechlich verwendet). active_index_version=0
    # bedeutet "noch nie erfolgreich indexiert".
    active_index_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_collection_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active_embedding_model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active_embedding_model_revision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active_chunking_strategie_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    active_chunk_ziel_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_chunk_overlap_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_index_erstellt_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Laufende Neuindexierung, getrennt gefuehrt (siehe Briefing).
    rebuild_status: Mapped[RebuildStatus] = mapped_column(
        SAEnum(RebuildStatus, native_enum=False, length=20), nullable=False, default=RebuildStatus.IDLE
    )
    pending_index_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pending_collection_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rebuild_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rebuild_error: Mapped[str | None] = mapped_column(Text, nullable=True)
