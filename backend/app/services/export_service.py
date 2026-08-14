import json
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models.chat import ChatConversation, ChatMessage
from app.db.models.document import Document, DocumentTag
from app.db.models.meeting import Meeting, MeetingParticipant
from app.db.models.person import Person
from app.db.models.tag import Tag
from app.db.models.task import Task, TaskDocument
from app.services.project_service import get_project

EXPORT_FORMAT = "project-a-export"
EXPORT_VERSION = 1
APP_VERSION = "0.1.0"


def _iso(value: object) -> str | None:
    return value.isoformat() if value is not None else None  # type: ignore[union-attr]


def export_project(db: Session, project_id: int) -> Path:
    """Baut ein ZIP mit Manifest + vollstaendigem projektbezogenen Datenbestand
    (Documents, Personen, Tasks, Meetings, Chats, Tags, Originaldateien) fuer
    genau ein Projekt (siehe Briefing Punkt 11: Projekt-Export, strikt
    getrennt vom System-Backup).

    Enthaelt bewusst NICHT: Chunks (abgeleitete Indexdaten, siehe
    Source-of-Truth-Prinzip - werden nach dem Import neu aufgebaut), den
    Claude-API-Key oder andere globale Programmeinstellungen (projekt-
    uebergreifend, nicht Teil eines einzelnen Projekts), ApiUsageLog
    (Kennzahlen zur Instanz, kein Projektinhalt).
    """
    project = get_project(db, project_id)
    settings = get_settings()

    documents = (
        db.query(Document)
        .filter(Document.project_id == project_id, Document.deleted_at.is_(None))
        .all()
    )
    tags = db.query(Tag).filter(Tag.project_id == project_id).all()
    document_tags = (
        db.query(DocumentTag)
        .join(Document, Document.id == DocumentTag.document_id)
        .filter(Document.project_id == project_id)
        .all()
    )
    people = db.query(Person).filter(Person.project_id == project_id).all()
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    task_documents = (
        db.query(TaskDocument)
        .join(Task, Task.id == TaskDocument.task_id)
        .filter(Task.project_id == project_id)
        .all()
    )
    meetings = db.query(Meeting).filter(Meeting.project_id == project_id).all()
    meeting_participants = (
        db.query(MeetingParticipant)
        .join(Meeting, Meeting.id == MeetingParticipant.meeting_id)
        .filter(Meeting.project_id == project_id)
        .all()
    )
    conversations = db.query(ChatConversation).filter(ChatConversation.project_id == project_id).all()
    conversation_ids = [c.id for c in conversations]
    messages = (
        db.query(ChatMessage).filter(ChatMessage.conversation_id.in_(conversation_ids)).all()
        if conversation_ids
        else []
    )

    data = {
        "project": {"name": project.name, "beschreibung": project.beschreibung},
        "documents": [
            {
                "id": d.id,
                "typ": d.typ.value,
                "titel": d.titel,
                "inhalt": d.inhalt,
                "ocr_text": d.ocr_text,
                "ki_analyse_rohtext": d.ki_analyse_rohtext,
                "datei_hash": d.datei_hash,
                "dateiname": d.dateiname,
                "hat_datei": d.original_dateipfad is not None,
                "dateiendung": Path(d.original_dateipfad).suffix if d.original_dateipfad else None,
                "dokumentdatum": _iso(d.dokumentdatum),
                "erstellt_am": _iso(d.erstellt_am),
                "aktualisiert_am": _iso(d.aktualisiert_am),
            }
            for d in documents
        ],
        "tags": [{"id": t.id, "name": t.name} for t in tags],
        "document_tags": [{"document_id": dt.document_id, "tag_id": dt.tag_id} for dt in document_tags],
        "people": [
            {
                "id": p.id,
                "name": p.name,
                "rolle": p.rolle,
                "kontaktinfo": p.kontaktinfo,
                "notizen": p.notizen,
            }
            for p in people
        ],
        "tasks": [
            {
                "id": t.id,
                "titel": t.titel,
                "beschreibung": t.beschreibung,
                "status": t.status.value,
                "zugewiesen_an": t.zugewiesen_an,
                "faellig_am": _iso(t.faellig_am),
            }
            for t in tasks
        ],
        "task_documents": [
            {"task_id": td.task_id, "document_id": td.document_id} for td in task_documents
        ],
        "meetings": [
            {
                "id": m.id,
                "datum": _iso(m.datum),
                "document_id": m.document_id,
                "zusammenfassung": m.zusammenfassung,
            }
            for m in meetings
        ],
        "meeting_participants": [
            {"meeting_id": mp.meeting_id, "person_id": mp.person_id} for mp in meeting_participants
        ],
        "chat_conversations": [
            {
                "id": c.id,
                "titel": c.titel,
                "erstellt_am": _iso(c.erstellt_am),
                "zuletzt_aktualisiert_am": _iso(c.zuletzt_aktualisiert_am),
            }
            for c in conversations
        ],
        "chat_messages": [
            {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "rolle": msg.rolle.value,
                "text": msg.text,
                "quellen": msg.quellen,
                "erstellt_am": _iso(msg.erstellt_am),
            }
            for msg in messages
        ],
    }

    manifest = {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "app_version": APP_VERSION,
    }

    tmp_dir = Path(tempfile.mkdtemp(prefix="project-a-export-"))
    zip_path = tmp_dir / f"project-{project_id}-export.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr("data.json", json.dumps(data, ensure_ascii=False, indent=2))
        for d in documents:
            if d.original_dateipfad:
                absolute_path = settings.uploads_dir / d.original_dateipfad
                if absolute_path.is_file():
                    extension = Path(d.original_dateipfad).suffix
                    zf.write(absolute_path, f"files/{d.id}/original{extension}")

    return zip_path
