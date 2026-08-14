from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.services import chat_service

router = APIRouter(prefix="/api/projects/{project_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def ask(project_id: int, payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    answer = chat_service.ask(db, project_id, payload.query)
    return ChatResponse(
        antwort=answer.antwort,
        quellen=answer.quellen,
        unbekannte_zitate=answer.unbekannte_zitate,
    )
