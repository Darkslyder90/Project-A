import io
import json
import shutil
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.background.task_runner import DocumentTaskRunner
from app.config import Settings, get_settings
from app.core.exceptions import ValidationAppError
from app.db.models.chat import ChatConversation, ChatMessage
from app.db.models.document import Document, DocumentTag
from app.db.models.enums import ChatRole, DocumentStatus, DocumentType, TaskStatus
from app.db.models.index_metadata import IndexMetadata
from app.db.models.meeting import Meeting, MeetingParticipant
from app.db.models.person import Person
from app.db.models.project import Project
from app.db.models.tag import Tag
from app.db.models.task import Task, TaskDocument
from app.security.file_safety import build_storage_relative_path

_EXPORT_FORMAT = "project-a-export"
_SUPPORTED_VERSIONS = {1}


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _safe_extract(zip_bytes: bytes, target_dir: Path) -> None:
    """Zip-Slip-Schutz (siehe Briefing): jeder Zielpfad wird VOR dem
    Extrahieren geprueft, ob er wirklich innerhalb von target_dir landet -
    ../ oder absolute Pfade im Archiv fuehren zu einem klaren Fehler statt
    stillschweigend ausserhalb des kontrollierten Verzeichnisses zu schreiben.
    """
    resolved_target = target_dir.resolve()
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for member in zf.infolist():
                member_path = (target_dir / member.filename).resolve()
                if not member_path.is_relative_to(resolved_target):
                    raise ValidationAppError(f"Unsicherer Pfad im Export-Archiv: {member.filename}")
            zf.extractall(target_dir)
    except zipfile.BadZipFile as exc:
        raise ValidationAppError("Datei ist kein gueltiges ZIP-Archiv.") from exc


def _build_project_graph(
    db: Session, data: dict, tmp_dir: Path, settings: Settings
) -> tuple[Project, dict[int, int]]:
    """Erzeugt Project + alle abhaengigen Entitaeten aus dem geparsten data.json
    innerhalb der uebergebenen Session (noch nicht committet). Gibt das neue
    Project sowie das Mapping alte->neue Document-ID zurueck (fuer das
    Einreihen zur Indexierung nach dem Commit). Wirft KeyError/TypeError/
    ValueError bei unerwarteter Struktur - der Aufrufer wandelt das in eine
    saubere ValidationAppError um.
    """
    project = Project(name=data["project"]["name"], beschreibung=data["project"].get("beschreibung"))
    db.add(project)
    db.flush()  # project.id fuer alle folgenden Fremdschluessel verfuegbar machen
    db.add(IndexMetadata(project_id=project.id))

    document_id_map: dict[int, int] = {}
    for doc_data in data["documents"]:
        document = Document(
            project_id=project.id,
            typ=DocumentType(doc_data["typ"]),
            titel=doc_data["titel"],
            inhalt=doc_data["inhalt"],
            ocr_text=doc_data.get("ocr_text"),
            ki_analyse_rohtext=doc_data.get("ki_analyse_rohtext"),
            datei_hash=doc_data.get("datei_hash"),
            dateiname=doc_data.get("dateiname"),
            # Unabhaengig vom urspruenglichen Status wird nach dem Import alles
            # neu eingeplant (siehe Briefing: automatische vollstaendige
            # Neuindexierung, Chroma ist fuer das neue Projekt zunaechst leer).
            status=DocumentStatus.PENDING,
            dokumentdatum=_parse_date(doc_data.get("dokumentdatum")),
        )
        if doc_data.get("erstellt_am"):
            document.erstellt_am = _parse_datetime(doc_data["erstellt_am"])
        if doc_data.get("aktualisiert_am"):
            document.aktualisiert_am = _parse_datetime(doc_data["aktualisiert_am"])
        db.add(document)
        db.flush()
        document_id_map[doc_data["id"]] = document.id

        if doc_data.get("hat_datei") and doc_data.get("dateiendung"):
            extension = doc_data["dateiendung"]
            source_file = tmp_dir / "files" / str(doc_data["id"]) / f"original{extension}"
            if source_file.is_file():
                relative_path = build_storage_relative_path(project.id, document.id, extension)
                absolute_path = settings.uploads_dir / relative_path
                absolute_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_file, absolute_path)
                document.original_dateipfad = relative_path

    tag_id_map: dict[int, int] = {}
    for tag_data in data["tags"]:
        tag = Tag(project_id=project.id, name=tag_data["name"])
        db.add(tag)
        db.flush()
        tag_id_map[tag_data["id"]] = tag.id

    for dt_data in data["document_tags"]:
        db.add(
            DocumentTag(
                document_id=document_id_map[dt_data["document_id"]],
                tag_id=tag_id_map[dt_data["tag_id"]],
            )
        )

    person_id_map: dict[int, int] = {}
    for person_data in data["people"]:
        person = Person(
            project_id=project.id,
            name=person_data["name"],
            rolle=person_data.get("rolle"),
            kontaktinfo=person_data.get("kontaktinfo"),
            notizen=person_data.get("notizen"),
        )
        db.add(person)
        db.flush()
        person_id_map[person_data["id"]] = person.id

    task_id_map: dict[int, int] = {}
    for task_data in data["tasks"]:
        zugewiesen_an = task_data.get("zugewiesen_an")
        task = Task(
            project_id=project.id,
            titel=task_data["titel"],
            beschreibung=task_data.get("beschreibung"),
            status=TaskStatus(task_data["status"]),
            zugewiesen_an=person_id_map.get(zugewiesen_an) if zugewiesen_an else None,
            faellig_am=_parse_date(task_data.get("faellig_am")),
        )
        db.add(task)
        db.flush()
        task_id_map[task_data["id"]] = task.id

    for td_data in data["task_documents"]:
        db.add(
            TaskDocument(
                task_id=task_id_map[td_data["task_id"]],
                document_id=document_id_map[td_data["document_id"]],
            )
        )

    meeting_id_map: dict[int, int] = {}
    for meeting_data in data["meetings"]:
        meeting_document_id = meeting_data.get("document_id")
        meeting = Meeting(
            project_id=project.id,
            datum=_parse_date(meeting_data["datum"]),
            document_id=document_id_map.get(meeting_document_id) if meeting_document_id else None,
            zusammenfassung=meeting_data.get("zusammenfassung"),
        )
        db.add(meeting)
        db.flush()
        meeting_id_map[meeting_data["id"]] = meeting.id

    for mp_data in data["meeting_participants"]:
        db.add(
            MeetingParticipant(
                meeting_id=meeting_id_map[mp_data["meeting_id"]],
                person_id=person_id_map[mp_data["person_id"]],
            )
        )

    conversation_id_map: dict[int, int] = {}
    for conv_data in data["chat_conversations"]:
        conversation = ChatConversation(project_id=project.id, titel=conv_data.get("titel"))
        if conv_data.get("erstellt_am"):
            conversation.erstellt_am = _parse_datetime(conv_data["erstellt_am"])
        if conv_data.get("zuletzt_aktualisiert_am"):
            conversation.zuletzt_aktualisiert_am = _parse_datetime(conv_data["zuletzt_aktualisiert_am"])
        db.add(conversation)
        db.flush()
        conversation_id_map[conv_data["id"]] = conversation.id

    for msg_data in data["chat_messages"]:
        quellen = msg_data.get("quellen")
        if quellen:
            quellen = [
                {**source, "document_id": document_id_map.get(source.get("document_id"))}
                for source in quellen
            ]
        message = ChatMessage(
            conversation_id=conversation_id_map[msg_data["conversation_id"]],
            rolle=ChatRole(msg_data["rolle"]),
            text=msg_data["text"],
            quellen=quellen,
        )
        if msg_data.get("erstellt_am"):
            message.erstellt_am = _parse_datetime(msg_data["erstellt_am"])
        db.add(message)

    return project, document_id_map


def import_project(db: Session, task_runner: DocumentTaskRunner, zip_bytes: bytes) -> Project:
    """Importiert einen zuvor per export_project() erzeugten Projekt-Export als
    NEUES Projekt (siehe Briefing: kein Ueberschreiben anhand gleicher IDs).
    Alle IDs werden remapped, alle Fremdschluessel-Beziehungen konsistent
    umgeschrieben. Transaktional: schlaegt irgendein Schritt fehl, wird die
    gesamte DB-Aenderung zurueckgerollt und bereits kopierte Dateien werden
    wieder entfernt - kein halbfertiges Projekt bleibt zurueck. Nach
    erfolgreichem Import wird jedes Dokument zur (Neu-)Indexierung eingereiht,
    da Chroma fuer das neue Projekt zunaechst leer ist.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="project-a-import-"))
    new_project_id: int | None = None
    try:
        _safe_extract(zip_bytes, tmp_dir)

        manifest_path = tmp_dir / "manifest.json"
        data_path = tmp_dir / "data.json"
        if not manifest_path.is_file() or not data_path.is_file():
            raise ValidationAppError("Ungueltiger Export: manifest.json oder data.json fehlt.")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format") != _EXPORT_FORMAT:
            raise ValidationAppError("Datei ist kein Project-A-Projekt-Export.")
        if manifest.get("version") not in _SUPPORTED_VERSIONS:
            raise ValidationAppError(
                f"Export-Version {manifest.get('version')!r} wird von dieser Project-A-Version "
                "nicht unterstuetzt."
            )

        data = json.loads(data_path.read_text(encoding="utf-8"))
        settings = get_settings()

        try:
            project, document_id_map = _build_project_graph(db, data, tmp_dir, settings)
            new_project_id = project.id
        except (KeyError, TypeError, ValueError) as exc:
            # data.json entspricht nicht der erwarteten Struktur (fehlendes Feld,
            # falscher Typ, ungueltiger Enum-Wert, ...) - klare Fehlermeldung statt
            # eines rohen 500ers, das Manifest allein reicht nicht als Garantie
            # fuer ein wohlgeformtes Archiv.
            raise ValidationAppError(f"Export-Datei ist beschaedigt oder unvollstaendig: {exc}") from exc

        db.commit()
        db.refresh(project)

        for new_document_id in document_id_map.values():
            task_runner.enqueue(new_document_id)

        return project
    except Exception:
        db.rollback()
        if new_project_id is not None:
            settings = get_settings()
            shutil.rmtree(settings.uploads_dir / str(new_project_id), ignore_errors=True)
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
