from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class RetrievalTestRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class RetrievalTestHitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    document_id: int
    document_titel: str
    vector_rank: int | None
    vector_score: float | None
    keyword_rank: int | None
    keyword_score: float | None
    fusion_rank: int
    gefunden_ueber: str
    text: str
    dokumenttyp: str | None
    dokumentdatum: date | None
    abschnitt: str | None
