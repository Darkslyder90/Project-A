from datetime import date

from pydantic import BaseModel, ConfigDict, Field


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
    eur_usd_wechselkurs: float | None = Field(default=None, gt=0)


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
    eur_usd_wechselkurs: float


class UsagePeriodSummary(BaseModel):
    anfragen: int
    tokens: int
    kosten_eur: float
    # False, wenn fuer mindestens einen Aufruf in diesem Zeitraum kein
    # passender Preis hinterlegt ist - kosten_eur ist dann eine Unterschaetzung.
    vollstaendig: bool


class UsageSummaryRead(BaseModel):
    heute: UsagePeriodSummary
    woche: UsagePeriodSummary
    monat: UsagePeriodSummary


class ModelPricingCreate(BaseModel):
    modell_name: str = Field(min_length=1, max_length=100)
    gueltig_ab: date
    input_preis_pro_million_usd: float = Field(ge=0)
    output_preis_pro_million_usd: float = Field(ge=0)
    cache_write_preis_pro_million_usd: float | None = Field(default=None, ge=0)
    cache_read_preis_pro_million_usd: float | None = Field(default=None, ge=0)


class ModelPricingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    modell_name: str
    gueltig_ab: date
    input_preis_pro_million_usd: float
    output_preis_pro_million_usd: float
    cache_write_preis_pro_million_usd: float | None
    cache_read_preis_pro_million_usd: float | None
