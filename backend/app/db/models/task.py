from datetime import date

from sqlalchemy import Date
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import TaskStatus


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    titel: Mapped[str] = mapped_column(String(300), nullable=False)
    beschreibung: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, native_enum=False, length=20), nullable=False, default=TaskStatus.OFFEN
    )
    # Person-Loeschung setzt dies auf NULL (siehe Briefing), Task bleibt bestehen.
    zugewiesen_an: Mapped[int | None] = mapped_column(
        ForeignKey("people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    faellig_am: Mapped[date | None] = mapped_column(Date, nullable=True)

    # viewonly: die eigentliche Pflege der Verknuepfung laeuft ueber
    # task_service.link_document/unlink_document (explizite TaskDocument-Zeilen),
    # diese Relationship dient nur der bequemen Auswertung beim Lesen (siehe
    # Task.dokument_ids), z. B. fuer die Uebersichtsseiten in Schritt 12.
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        secondary="task_documents", viewonly=True, order_by="Document.titel"
    )

    @property
    def dokument_ids(self) -> list[int]:
        return [d.id for d in self.documents]


class TaskDocument(Base):
    __tablename__ = "task_documents"

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
