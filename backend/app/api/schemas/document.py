from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import DocumentStatus, DocumentType

# Manuelle Eingabe (Schritt 3) deckt nur Typen ab, die ohne Datei/Bild sinnvoll
# sind - "datei" und "bild" kommen erst mit Upload (Schritt 7/9) dazu.
MANUAL_DOCUMENT_TYPES = (
    DocumentType.MEETING,
    DocumentType.SYSTEMEINSTELLUNG,
    DocumentType.PROZESS,
    DocumentType.NOTIZ,
    DocumentType.SONSTIGES,
)


class DocumentCreate(BaseModel):
    typ: DocumentType
    titel: str = Field(min_length=1, max_length=300)
    inhalt: str = Field(min_length=1)
    dokumentdatum: date | None = None


class DocumentReviewSubmit(BaseModel):
    """Bestaetigung/Bearbeitung der KI-Bildanalyse im Review-Schritt (Schritt 9)."""

    inhalt: str = Field(min_length=1)


class DocumentUpdate(BaseModel):
    """Nachtraegliche Bearbeitung (siehe Briefing Punkt 6: Titel, Inhalt, Typ,
    Dokumentdatum sind editierbar). Alle Felder optional (PATCH-Semantik ueber
    model_fields_set, siehe document_service.update_document) - Tags werden
    weiterhin ueber die eigenen Tag-Endpunkte gepflegt, nicht hier.
    """

    titel: str | None = Field(default=None, min_length=1, max_length=300)
    inhalt: str | None = Field(default=None, min_length=1)
    typ: DocumentType | None = None
    dokumentdatum: date | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    typ: DocumentType
    titel: str
    inhalt: str | None
    ocr_text: str | None
    ki_analyse_rohtext: str | None
    status: DocumentStatus
    fehlermeldung: str | None
    dokumentdatum: date | None
    dateiname: str | None
    erstellt_am: datetime
    aktualisiert_am: datetime
    tag_ids: list[int]
