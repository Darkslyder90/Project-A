from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppSettings(Base):
    """Globale, projektuebergreifende Programmeinstellungen - genau eine Zeile
    (id=1), lazy angelegt vom settings_service. Der Claude-API-Key ist hier
    (verschluesselt) global, NICHT pro Projekt (siehe Briefing).

    max_upload_size_mb ist bewusst NICHT hier, sondern in config.py/.env - das
    Briefing ordnet es explizit dem .env zu, nicht den Laufzeit-Settings.
    """

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Fernet-Ciphertext, niemals der Klartext. Verschluesselung/Entschluesselung
    # nutzt settings_encryption_key aus der Umgebung (siehe config.py).
    claude_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    claude_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Unabhaengig vom Claude-Modell (siehe Briefing Tech-Stack-Abschnitt).
    embedding_model_name: Mapped[str] = mapped_column(String(200), nullable=False, default="intfloat/multilingual-e5-base")

    # RAG-Feintuning, siehe Briefing Punkt 7/11.
    candidate_k_vector: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    candidate_k_keyword: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    final_k: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    chunk_ziel_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=350)
    chunk_overlap_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    fusion_verfahren: Mapped[str] = mapped_column(String(50), nullable=False, default="rrf")

    # Manuell gepflegter Umrechnungskurs (wie viele Euro entsprechen 1 US-Dollar,
    # siehe pricing_service.py) - kein automatischer Kursabruf (siehe Briefing-
    # Geist: einfache, nachvollziehbare Loesungen statt zusaetzlicher externer
    # Abhaengigkeit fuer eine reine Schaetzanzeige).
    eur_usd_wechselkurs: Mapped[float] = mapped_column(Float, nullable=False, default=0.92)
