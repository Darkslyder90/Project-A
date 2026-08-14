from datetime import datetime

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.models.enums import ApiUsagePurpose


class ApiUsageLog(Base):
    """Reine Kennzahlen zu Claude-API-Aufrufen - NIEMALS vollstaendige Prompts,
    Projekttexte oder Chat-Inhalte (siehe Briefing, Datenschutz-Prinzip).
    """

    __tablename__ = "api_usage_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable: manche Aufrufe sind keinem Projekt zuordenbar. Projekt-Loeschung
    # entfernt per CASCADE auch die zugehoerigen Log-Zeilen (siehe Briefing Punkt 6).
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    zweck: Mapped[ApiUsagePurpose] = mapped_column(
        SAEnum(ApiUsagePurpose, native_enum=False, length=30), nullable=False
    )
    modell: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dauer_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    erfolg: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fehlertyp: Mapped[str | None] = mapped_column(String(200), nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
