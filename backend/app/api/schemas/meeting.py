from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class MeetingCreate(BaseModel):
    datum: date
    # Optional (siehe Meeting-Modell): ein Meeting kann auch ohne Protokoll-
    # Dokument angelegt werden.
    document_id: int | None = None
    zusammenfassung: str | None = None
    teilnehmer_ids: list[int] = Field(default_factory=list)


class MeetingUpdate(BaseModel):
    datum: date | None = None
    zusammenfassung: str | None = None
    # Erlaubt nachtraeglich ein Protokoll-Dokument zuzuweisen oder zu wechseln;
    # explizit auf null gesetzt entfernt die Verknuepfung wieder (Dokument
    # selbst wird dabei NICHT geloescht, siehe meeting_service.update_meeting).
    document_id: int | None = None


class MeetingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    datum: date
    document_id: int | None
    zusammenfassung: str | None
    teilnehmer_ids: list[int]
