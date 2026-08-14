from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.chat import (
    ChatConversationDetail,
    ChatConversationRead,
    ChatConversationUpdate,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services import chat_conversation_service as service

router = APIRouter(prefix="/api/projects/{project_id}/chat/conversations", tags=["chat"])


@router.get("", response_model=list[ChatConversationRead])
def list_conversations(project_id: int, db: Session = Depends(get_db)) -> list[ChatConversationRead]:
    return service.list_conversations(db, project_id)


@router.post("", response_model=ChatConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(project_id: int, db: Session = Depends(get_db)) -> ChatConversationRead:
    return service.create_conversation(db, project_id)


@router.get("/{conversation_id}", response_model=ChatConversationDetail)
def get_conversation(
    project_id: int, conversation_id: int, db: Session = Depends(get_db)
) -> ChatConversationDetail:
    conversation = service.get_conversation(db, project_id, conversation_id)
    messages = service.list_messages(db, project_id, conversation_id)
    return ChatConversationDetail(
        id=conversation.id,
        project_id=conversation.project_id,
        titel=conversation.titel,
        erstellt_am=conversation.erstellt_am,
        zuletzt_aktualisiert_am=conversation.zuletzt_aktualisiert_am,
        nachrichten=[service.to_message_read(db, m) for m in messages],
    )


@router.patch("/{conversation_id}", response_model=ChatConversationRead)
def rename_conversation(
    project_id: int,
    conversation_id: int,
    payload: ChatConversationUpdate,
    db: Session = Depends(get_db),
) -> ChatConversationRead:
    return service.rename_conversation(db, project_id, conversation_id, payload.titel)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(project_id: int, conversation_id: int, db: Session = Depends(get_db)) -> None:
    service.delete_conversation(db, project_id, conversation_id)


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
def send_message(
    project_id: int,
    conversation_id: int,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
) -> SendMessageResponse:
    conversation, assistant_message = service.send_message(
        db, project_id, conversation_id, payload.query
    )
    return SendMessageResponse(
        conversation=conversation,
        nachricht=service.to_message_read(db, assistant_message),
    )
