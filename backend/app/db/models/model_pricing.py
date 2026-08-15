from datetime import date

from sqlalchemy import Date, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelPricing(Base):
    """Preise pro Claude-Modell, zeitlich versioniert (siehe Briefing-Geist:
    reine Kennzahlen/Schaetzungen, keine Kostenspeicherung - hier die
    Preis-Grundlage dafuer). Mehrere Zeilen pro Modell moeglich (eine je
    Preisaenderung); `gueltig_ab` legt fest, ab wann ein Preis gilt. Historische
    Auswertungen bleiben dadurch korrekt, auch wenn sich Preise spaeter aendern -
    pricing_service waehlt je Nutzungs-Log-Eintrag den zum jeweiligen Zeitpunkt
    gueltigen Preis, nicht den aktuellsten. Keine Zuordnung zu einem Projekt -
    Preise sind wie das Claude-Modell selbst eine globale Einstellung.

    Preise in USD pro 1 Million Tokens, wie von Anthropic veroeffentlicht.
    cache_write/cache_read sind optional (nullable), da aktuell keine
    Prompt-Caching-Nutzung in ApiUsageLog erfasst wird - fuer spaetere
    Erweiterung bereits im Datenmodell vorgesehen.
    """

    __tablename__ = "model_pricing"
    __table_args__ = (
        UniqueConstraint("modell_name", "gueltig_ab", name="uq_model_pricing_modell_gueltig_ab"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    modell_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    gueltig_ab: Mapped[date] = mapped_column(Date, nullable=False)

    input_preis_pro_million_usd: Mapped[float] = mapped_column(Float, nullable=False)
    output_preis_pro_million_usd: Mapped[float] = mapped_column(Float, nullable=False)
    cache_write_preis_pro_million_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    cache_read_preis_pro_million_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
