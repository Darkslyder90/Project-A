from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.api.schemas.chat import ChatMessageRead, ChatSourceSnapshot
from app.chat.claude_client import call_claude
from app.chat.prompt_builder import build_system_prompt
from app.chat.source_validator import extract_cited_source_ids
from app.core.exceptions import NotFoundError
from app.db.models.chat import ChatConversation, ChatMessage
from app.db.models.document import Document
from app.db.models.enums import ApiUsagePurpose, ChatRole
from app.services.chat_service import build_sources
from app.services.project_service import get_project
from app.services.settings_service import get_app_settings

_TITEL_MAX_LEN = 80
_ZITAT_AUSSCHNITT_MAX_LEN = 300


def list_conversations(db: Session, project_id: int) -> list[ChatConversation]:
    get_project(db, project_id)
    return (
        db.query(ChatConversation)
        .filter(ChatConversation.project_id == project_id)
        .order_by(ChatConversation.zuletzt_aktualisiert_am.desc())
        .all()
    )


def get_conversation(db: Session, project_id: int, conversation_id: int) -> ChatConversation:
    conversation = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.project_id == project_id,
        )
        .first()
    )
    if conversation is None:
        raise NotFoundError(
            f"Konversation {conversation_id} wurde in Projekt {project_id} nicht gefunden."
        )
    return conversation


def create_conversation(db: Session, project_id: int) -> ChatConversation:
    get_project(db, project_id)
    conversation = ChatConversation(project_id=project_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def rename_conversation(
    db: Session, project_id: int, conversation_id: int, titel: str
) -> ChatConversation:
    conversation = get_conversation(db, project_id, conversation_id)
    conversation.titel = titel
    db.commit()
    db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, project_id: int, conversation_id: int) -> None:
    conversation = get_conversation(db, project_id, conversation_id)
    db.delete(conversation)
    db.commit()


def list_messages(db: Session, project_id: int, conversation_id: int) -> list[ChatMessage]:
    get_conversation(db, project_id, conversation_id)
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.erstellt_am.asc())
        .all()
    )


def to_message_read(db: Session, message: ChatMessage) -> ChatMessageRead:
    """Loest den gespeicherten Quellen-Snapshot in ein Response-Objekt auf und
    prueft dabei live, ob das referenzierte Document noch existiert (siehe
    Briefing: "Quelle wurde inzwischen geloescht" statt defektem Link).
    """
    quellen = None
    if message.quellen:
        document_ids = {q["document_id"] for q in message.quellen}
        existing_ids = {
            d.id for d in db.query(Document.id).filter(Document.id.in_(document_ids)).all()
        }
        quellen = [
            ChatSourceSnapshot(
                source_id=q["source_id"],
                document_id=q["document_id"],
                document_titel=q["document_titel"],
                dokumentdatum=q.get("dokumentdatum"),
                abschnitt=q.get("abschnitt"),
                text_ausschnitt=q["text_ausschnitt"],
                geloescht=q["document_id"] not in existing_ids,
            )
            for q in message.quellen
        ]
    return ChatMessageRead(
        id=message.id,
        conversation_id=message.conversation_id,
        rolle=message.rolle,
        text=message.text,
        quellen=quellen,
        erstellt_am=message.erstellt_am,
    )


def send_message(
    db: Session, project_id: int, conversation_id: int, query: str
) -> tuple[ChatConversation, ChatMessage]:
    conversation = get_conversation(db, project_id, conversation_id)

    prior_messages = list_messages(db, project_id, conversation_id)

    # Nutzer-Nachricht sofort persistieren und committen - bleibt auch dann
    # erhalten, wenn der nachfolgende Claude-Aufruf fehlschlaegt (siehe
    # Briefing: Claude-Ausfall darf App nicht lahmlegen; die gestellte Frage
    # geht dabei nicht verloren).
    user_message = ChatMessage(conversation_id=conversation.id, rolle=ChatRole.USER, text=query)
    db.add(user_message)
    if conversation.titel is None:
        conversation.titel = query[:_TITEL_MAX_LEN]
    conversation.zuletzt_aktualisiert_am = datetime.now(UTC)
    db.commit()

    # Konversationsverlauf dient nur der Kontextaufloesung, nicht als eigene
    # Wissensquelle (siehe Briefing) - fachliche Grundlage ist ausschliesslich
    # die fuer DIESE Anfrage frisch retrievte Quellenliste.
    app_settings = get_app_settings(db)
    sources = build_sources(db, project_id, query, app_settings.final_k)
    system_prompt = build_system_prompt(sources)

    claude_messages = [{"role": m.rolle.value, "content": m.text} for m in prior_messages]
    claude_messages.append({"role": "user", "content": query})

    result = call_claude(
        db,
        project_id=project_id,
        system=system_prompt,
        messages=claude_messages,
        zweck=ApiUsagePurpose.CHAT,
    )

    if result.stop_reason == "refusal":
        answer_text = "Claude konnte diese Anfrage leider nicht beantworten."
        used_sources = []
    else:
        valid_ids = {s.source_id for s in sources}
        cited_ids = extract_cited_source_ids(result.text) & valid_ids
        used_sources = [s for s in sources if s.source_id in cited_ids]
        answer_text = result.text

    quellen_snapshot = [
        {
            "source_id": s.source_id,
            "document_id": s.document_id,
            "document_titel": s.document_titel,
            "dokumentdatum": s.dokumentdatum.isoformat() if s.dokumentdatum else None,
            "abschnitt": s.abschnitt,
            "text_ausschnitt": s.text[:_ZITAT_AUSSCHNITT_MAX_LEN],
        }
        for s in used_sources
    ]

    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        rolle=ChatRole.ASSISTANT,
        text=answer_text,
        quellen=quellen_snapshot or None,
    )
    db.add(assistant_message)
    conversation.zuletzt_aktualisiert_am = datetime.now(UTC)
    db.commit()
    db.refresh(assistant_message)
    db.refresh(conversation)

    return conversation, assistant_message
