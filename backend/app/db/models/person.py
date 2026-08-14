from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rolle: Mapped[str | None] = mapped_column(String(200), nullable=True)
    kontaktinfo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    notizen: Mapped[str | None] = mapped_column(Text, nullable=True)
