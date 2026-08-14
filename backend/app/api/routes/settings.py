from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.settings import AppSettingsRead, AppSettingsUpdate, UsageSummaryRead
from app.services import settings_service

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
