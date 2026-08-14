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


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    typ: DocumentType
    titel: str
    inhalt: str | None
    status: DocumentStatus
    fehlermeldung: str | None
    dokumentdatum: date | None
    erstellt_am: datetime
    aktualisiert_am: datetime
