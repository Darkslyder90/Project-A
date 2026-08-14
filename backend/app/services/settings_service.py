from sqlalchemy.orm import Session

from app.db.models.app_settings import AppSettings

_SINGLETON_ID = 1


def get_app_settings(db: Session) -> AppSettings:
    """Liefert die eine globale Settings-Zeile, legt sie mit Modell-Defaults an,
    falls sie noch nicht existiert (siehe AppSettings-Modell). Wird sowohl von
    der spaeteren Settings-UI (Schritt 13) als auch schon jetzt von der
    Ingestion-Pipeline genutzt (Embedding-Modell, Chunk-Groesse).
    """
    settings_row = db.get(AppSettings, _SINGLETON_ID)
    if settings_row is None:
        settings_row = AppSettings(id=_SINGLETON_ID)
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row
