from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)


class ChatSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    document_id: int
    document_titel: str
    dokumentdatum: date | None
    abschnitt: str | None
    text: str


class ChatResponse(BaseModel):
    antwort: str
    quellen: list[ChatSourceRead]
    unbekannte_zitate: list[str]
