import io
import json
import zipfile

from app.chat import claude_client as claude_client_module
from tests.helpers import wait_for_document_status


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeUsage:
    def __init__(self) -> None:
        self.input_tokens = 10
        self.output_tokens = 5


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeTextBlock(text)]
        self.usage = _FakeUsage()
        self.stop_reason = "end_turn"
        self.model = "claude-opus-5"


class _FakeMessagesResource:
    def __init__(self, text: str) -> None:
        self._text = text

    def create(self, *, model, max_tokens, system, messages):  # noqa: ARG002
        return _FakeMessage(self._text)


class _FakeAnthropicClient:
    def __init__(self, messages_resource: _FakeMessagesResource) -> None:
        self.messages = messages_resource


def _patch_claude(monkeypatch, text: str) -> None:
    def _factory(api_key=None):  # noqa: ARG001
        return _FakeAnthropicClient(_FakeMessagesResource(text))

    monkeypatch.setattr(claude_client_module.anthropic, "Anthropic", _factory)


def _create_project(client, name: str = "Export-Testprojekt") -> int:
    return client.post("/api/projects", json={"name": name, "beschreibung": "Eine Beschreibung."}).json()["id"]


def _build_rich_project(client, monkeypatch) -> dict:
    """Legt ein Projekt mit je einem Eintrag pro Entitaetstyp an, inkl.
    Verknuepfungen, und liefert die wichtigsten IDs zurueck.
    """
    project_id = _create_project(client)

    doc = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "meeting", "titel": "Protokoll", "inhalt": "Wichtiger Inhalt ueber SAP VA02."},
    ).json()
    wait_for_document_status(client, project_id, doc["id"])

    client.post(f"/api/projects/{project_id}/documents/{doc['id']}/tags", json={"name": "Wichtig"})

    uploaded = client.post(
        f"/api/projects/{project_id}/documents/upload",
        files={"file": ("notiz.txt", b"Hochgeladener Originalinhalt.", "text/plain")},
        data={"typ": "notiz"},
    ).json()
    wait_for_document_status(client, project_id, uploaded["id"])

    person = client.post(f"/api/projects/{project_id}/people", json={"name": "Anna Weber", "rolle": "Beraterin"}).json()

    task = client.post(
        f"/api/projects/{project_id}/tasks",
        json={"titel": "Nacharbeiten", "zugewiesen_an": person["id"], "dokument_ids": [doc["id"]]},
    ).json()

    meeting = client.post(
        f"/api/projects/{project_id}/meetings",
        json={"datum": "2026-08-01", "document_id": doc["id"], "teilnehmer_ids": [person["id"]], "zusammenfassung": "Kurz."},
    ).json()

    _patch_claude(monkeypatch, "Die Antwort bezieht sich auf [S1].")
    conversation_id = client.post(f"/api/projects/{project_id}/chat/conversations").json()["id"]
    client.post(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}/messages",
        json={"query": "Worum geht es im Protokoll?"},
    )

    return {
        "project_id": project_id,
        "document_id": doc["id"],
        "uploaded_document_id": uploaded["id"],
        "person_id": person["id"],
        "task_id": task["id"],
        "meeting_id": meeting["id"],
        "conversation_id": conversation_id,
    }


def _import_zip(client, zip_bytes: bytes, filename: str = "export.zip"):
    return client.post(
        "/api/projects/import",
        files={"file": (filename, zip_bytes, "application/zip")},
    )


def test_export_returns_zip_with_manifest_and_data(client, monkeypatch):
    ids = _build_rich_project(client, monkeypatch)

    response = client.get(f"/api/projects/{ids['project_id']}/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "data.json" in names
        assert any(n.startswith(f"files/{ids['uploaded_document_id']}/") for n in names)

        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["format"] == "project-a-export"
        assert manifest["version"] == 1

        data = json.loads(zf.read("data.json"))
        assert data["project"]["name"] == "Export-Testprojekt"
        assert len(data["documents"]) == 2
        assert len(data["tasks"]) == 1
        assert len(data["meetings"]) == 1
        assert len(data["chat_messages"]) == 2  # user + assistant


def test_export_for_unknown_project_returns_404(client):
    assert client.get("/api/projects/999999/export").status_code == 404


def test_import_roundtrip_preserves_data_with_remapped_ids(client, app, monkeypatch):
    ids = _build_rich_project(client, monkeypatch)

    # Welches Dokument tatsaechlich zitiert wurde, haengt von der Embedding-
    # Aehnlichkeit zwischen den zwei im Projekt vorhandenen Dokumenten ab (nicht
    # deterministisch vorhersehbar) - der Titel wird hier vor dem Export notiert,
    # um nach dem Import zu pruefen, dass das REMAPPING konsistent blieb, ohne
    # anzunehmen, welches der beiden Dokumente zitiert wurde.
    original_detail = client.get(
        f"/api/projects/{ids['project_id']}/chat/conversations/{ids['conversation_id']}"
    ).json()
    original_cited_document_id = original_detail["nachrichten"][1]["quellen"][0]["document_id"]
    original_cited_titel = client.get(
        f"/api/projects/{ids['project_id']}/documents/{original_cited_document_id}"
    ).json()["titel"]

    zip_bytes = client.get(f"/api/projects/{ids['project_id']}/export").content

    imported = _import_zip(client, zip_bytes)
    assert imported.status_code == 201
    new_project = imported.json()
    new_project_id = new_project["id"]
    assert new_project_id != ids["project_id"]
    assert new_project["name"] == "Export-Testprojekt"

    new_docs = client.get(f"/api/projects/{new_project_id}/documents").json()
    assert len(new_docs) == 2
    new_doc = next(d for d in new_docs if d["titel"] == "Protokoll")
    new_uploaded_doc = next(d for d in new_docs if d["titel"] == "notiz")
    assert new_doc["id"] != ids["document_id"]
    assert new_doc["tag_ids"] != []

    ready = wait_for_document_status(client, new_project_id, new_doc["id"])
    assert ready["status"] == "ready"
    assert ready["inhalt"] == "Wichtiger Inhalt ueber SAP VA02."

    wait_for_document_status(client, new_project_id, new_uploaded_doc["id"])
    file_response = client.get(f"/api/projects/{new_project_id}/documents/{new_uploaded_doc['id']}/file")
    assert file_response.status_code == 200
    assert file_response.content == b"Hochgeladener Originalinhalt."

    new_people = client.get(f"/api/projects/{new_project_id}/people").json()
    assert len(new_people) == 1
    assert new_people[0]["name"] == "Anna Weber"

    new_tasks = client.get(f"/api/projects/{new_project_id}/tasks").json()
    assert len(new_tasks) == 1
    assert new_tasks[0]["zugewiesen_an"] == new_people[0]["id"]
    assert new_tasks[0]["dokument_ids"] == [new_doc["id"]]

    new_meetings = client.get(f"/api/projects/{new_project_id}/meetings").json()
    assert len(new_meetings) == 1
    assert new_meetings[0]["document_id"] == new_doc["id"]
    assert new_meetings[0]["teilnehmer_ids"] == [new_people[0]["id"]]

    new_conversations = client.get(f"/api/projects/{new_project_id}/chat/conversations").json()
    assert len(new_conversations) == 1
    detail = client.get(
        f"/api/projects/{new_project_id}/chat/conversations/{new_conversations[0]['id']}"
    ).json()
    assert len(detail["nachrichten"]) == 2
    assistant_message = detail["nachrichten"][1]
    new_cited_document_id = assistant_message["quellen"][0]["document_id"]
    new_cited_titel = next(d["titel"] for d in new_docs if d["id"] == new_cited_document_id)
    assert new_cited_titel == original_cited_titel

    # Chunks wurden fuer das neue Projekt tatsaechlich neu aufgebaut (siehe Briefing:
    # Chroma ist nach Import zunaechst leer, vollstaendige Neuindexierung noetig).
    from app.db.models.chunk import Chunk

    with app.state.session_factory() as db:
        assert db.query(Chunk).filter(Chunk.document_id == new_doc["id"]).count() >= 1


def test_import_twice_creates_two_separate_projects(client, monkeypatch):
    ids = _build_rich_project(client, monkeypatch)
    zip_bytes = client.get(f"/api/projects/{ids['project_id']}/export").content

    first = _import_zip(client, zip_bytes).json()
    second = _import_zip(client, zip_bytes).json()
    assert first["id"] != second["id"]


def test_import_rejects_garbage_bytes(client):
    response = _import_zip(client, b"das ist definitiv kein zip")
    assert response.status_code == 422


def test_import_rejects_zip_with_wrong_manifest_format(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "irgendwas-anderes", "version": 1}))
        zf.writestr("data.json", json.dumps({}))
    response = _import_zip(client, buf.getvalue())
    assert response.status_code == 422


def test_import_rejects_unsupported_version(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "project-a-export", "version": 999}))
        zf.writestr("data.json", json.dumps({}))
    response = _import_zip(client, buf.getvalue())
    assert response.status_code == 422


def test_import_rejects_zip_slip_path(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "project-a-export", "version": 1}))
        zf.writestr("../evil.txt", "boese")
    response = _import_zip(client, buf.getvalue())
    assert response.status_code == 422


def test_import_with_no_project_created_on_failure(client, app):
    from app.db.models.project import Project

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Gueltiges Manifest, aber data.json fehlt komplett benoetigte Schluessel
        # (z. B. "documents") - muss sauber fehlschlagen, kein Teil-Projekt uebrig.
        zf.writestr("manifest.json", json.dumps({"format": "project-a-export", "version": 1}))
        zf.writestr("data.json", json.dumps({"project": {"name": "Kaputt"}}))

    with app.state.session_factory() as db:
        before = db.query(Project).count()

    response = _import_zip(client, buf.getvalue())
    assert response.status_code >= 400

    with app.state.session_factory() as db:
        after = db.query(Project).count()
    assert after == before


def test_export_excludes_soft_deleted_documents(client, app):
    project_id = _create_project(client)
    doc = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": "Wird geloescht", "inhalt": "Text."},
    ).json()
    wait_for_document_status(client, project_id, doc["id"])
    client.delete(f"/api/projects/{project_id}/documents/{doc['id']}")

    zip_bytes = client.get(f"/api/projects/{project_id}/export").content
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        data = json.loads(zf.read("data.json"))
    assert data["documents"] == []


def test_meeting_without_document_roundtrips(client):
    project_id = _create_project(client)
    client.post(f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-01"})

    zip_bytes = client.get(f"/api/projects/{project_id}/export").content
    imported = _import_zip(client, zip_bytes).json()

    meetings = client.get(f"/api/projects/{imported['id']}/meetings").json()
    assert len(meetings) == 1
    assert meetings[0]["document_id"] is None
