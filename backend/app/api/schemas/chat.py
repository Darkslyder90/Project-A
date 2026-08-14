from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import ChatRole


class ChatConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    titel: str | None
    erstellt_am: datetime
    zuletzt_aktualisiert_am: datetime


class ChatConversationUpdate(BaseModel):
    titel: str = Field(min_length=1, max_length=300)


class ChatSourceSnapshot(BaseModel):
    """Quellen-Snapshot (siehe Briefing): damalige Metadaten zum Zeitpunkt der
    Antwort, unabhaengig vom aktuellen Zustand des Documents. `geloescht` wird
    beim Lesen live berechnet (Document existiert noch oder nicht), nicht
    gespeichert.
    """

    source_id: str
    document_id: int
    document_titel: str
    dokumentdatum: date | None
    abschnitt: str | None
    text_ausschnitt: str
    geloescht: bool = False


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    rolle: ChatRole
    text: str
    quellen: list[ChatSourceSnapshot] | None
    erstellt_am: datetime


class ChatConversationDetail(ChatConversationRead):
    nachrichten: list[ChatMessageRead]


class SendMessageRequest(BaseModel):
    query: str = Field(min_length=1)


class SendMessageResponse(BaseModel):
    conversation: ChatConversationRead
    nachricht: ChatMessageRead
