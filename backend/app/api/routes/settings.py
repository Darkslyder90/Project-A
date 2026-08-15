from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.settings import (
    AppSettingsRead,
    AppSettingsUpdate,
    ModelPricingCreate,
    ModelPricingRead,
    UsageSummaryRead,
)
from app.services import pricing_service, settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_read(db: Session) -> AppSettingsRead:
    app_settings = settings_service.get_app_settings(db)
    status_, masked = settings_service.get_api_key_status(db)
    return AppSettingsRead(
        claude_api_key_status=status_,
        claude_api_key_masked=masked,
        claude_model=app_settings.claude_model,
        effective_claude_model=settings_service.resolve_effective_claude_model(db),
        embedding_model_name=app_settings.embedding_model_name,
        candidate_k_vector=app_settings.candidate_k_vector,
        candidate_k_keyword=app_settings.candidate_k_keyword,
        final_k=app_settings.final_k,
        chunk_ziel_tokens=app_settings.chunk_ziel_tokens,
        chunk_overlap_tokens=app_settings.chunk_overlap_tokens,
        fusion_verfahren=app_settings.fusion_verfahren,
        eur_usd_wechselkurs=app_settings.eur_usd_wechselkurs,
    )


@router.get("", response_model=AppSettingsRead)
def get_settings_endpoint(db: Session = Depends(get_db)) -> AppSettingsRead:
    return _to_read(db)


@router.patch("", response_model=AppSettingsRead)
def update_settings_endpoint(payload: AppSettingsUpdate, db: Session = Depends(get_db)) -> AppSettingsRead:
    settings_service.update_app_settings(db, payload)
    return _to_read(db)


@router.get("/usage", response_model=UsageSummaryRead)
def get_usage_endpoint(db: Session = Depends(get_db)) -> UsageSummaryRead:
    return settings_service.get_usage_summary(db)


@router.get("/pricing", response_model=list[ModelPricingRead])
def list_pricing_endpoint(db: Session = Depends(get_db)) -> list[ModelPricingRead]:
    return pricing_service.list_pricing(db)


@router.post("/pricing", response_model=ModelPricingRead, status_code=status.HTTP_201_CREATED)
def create_pricing_endpoint(payload: ModelPricingCreate, db: Session = Depends(get_db)) -> ModelPricingRead:
    return pricing_service.create_pricing(
        db,
        modell_name=payload.modell_name,
        gueltig_ab=payload.gueltig_ab,
        input_preis_pro_million_usd=payload.input_preis_pro_million_usd,
        output_preis_pro_million_usd=payload.output_preis_pro_million_usd,
        cache_write_preis_pro_million_usd=payload.cache_write_preis_pro_million_usd,
        cache_read_preis_pro_million_usd=payload.cache_read_preis_pro_million_usd,
    )


@router.delete("/pricing/{pricing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pricing_endpoint(pricing_id: int, db: Session = Depends(get_db)) -> None:
    pricing_service.delete_pricing(db, pricing_id)
