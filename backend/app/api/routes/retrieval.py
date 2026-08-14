from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.retrieval import RetrievalTestHitRead, RetrievalTestRequest
from app.services import retrieval_service

router = APIRouter(prefix="/api/projects/{project_id}/retrieval-test", tags=["retrieval"])


@router.post("", response_model=list[RetrievalTestHitRead])
def test_retrieval(
    project_id: int, payload: RetrievalTestRequest, db: Session = Depends(get_db)
) -> list[RetrievalTestHitRead]:
    return retrieval_service.test_retrieval(db, project_id, payload.query, payload.top_k)
