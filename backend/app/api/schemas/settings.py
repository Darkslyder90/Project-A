from pydantic import BaseModel, Field


class AppSettingsUpdate(BaseModel):
    """Alle Felder optional (PATCH-Semantik ueber model_fields_set, siehe
    settings_service.update_app_settings). claude_api_key: weggelassen =
    unveraendert, "" = gespeicherten Key entfernen, sonst = neuen Key setzen
    (wird sofort verschluesselt, der Klartext wird nirgends gespeichert).
    """

    claude_api_key: str | None = None
    claude_model: str | None = None
    embedding_model_name: str | None = Field(default=None, min_length=1)
    candidate_k_vector: int | None = Field(default=None, ge=1, le=200)
    candidate_k_keyword: int | None = Field(default=None, ge=1, le=200)
    final_k: int | None = Field(default=None, ge=1, le=50)
    chunk_ziel_tokens: int | None = Field(default=None, ge=50, le=2000)
    chunk_overlap_tokens: int | None = Field(default=None, ge=0, le=500)


class AppSettingsRead(BaseModel):
    # claude_api_key_status: "db" (in SQLite gespeichert, entschluesselbar),
    # "db_invalid" (gespeichert, aber nicht entschluesselbar - fehlendes/
    # geaendertes SETTINGS_ENCRYPTION_KEY), "env" (.env-Fallback aktiv),
    # "none" (kein Key verfuegbar).
    claude_api_key_status: str
    claude_api_key_masked: str | None
    claude_model: str | None
    effective_claude_model: str
    embedding_model_name: str
    candidate_k_vector: int
    candidate_k_keyword: int
    final_k: int
    chunk_ziel_tokens: int
    chunk_overlap_tokens: int
    fusion_verfahren: str


class UsagePeriodSummary(BaseModel):
    anfragen: int
    tokens: int


class UsageSummaryRead(BaseModel):
    heute: UsagePeriodSummary
    woche: UsagePeriodSummary
    monat: UsagePeriodSummary
