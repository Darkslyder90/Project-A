from app.chat import claude_client as claude_client_module
from tests.helpers import wait_for_document_status


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeUsage:
    def __init__(self) -> None:
        self.input_tokens = 500
        self.output_tokens = 80


class _FakeMessage:
    def __init__(self, text: str, stop_reason: str, model: str) -> None:
        self.content = [_FakeTextBlock(text)]
        self.usage = _FakeUsage()
        self.stop_reason = stop_reason
        self.model = model


class _FakeMessagesResource:
    def __init__(self, text: str, stop_reason: str) -> None:
        self._text = text
        self._stop_reason = stop_reason
        self.last_messages: list[dict] | None = None

    def create(self, *, model, max_tokens, system, messages):  # noqa: ARG002
        self.last_messages = messages
        return _FakeMessage(self._text, self._stop_reason, model)


class _FakeAnthropicClient:
    def __init__(self, messages_resource: _FakeMessagesResource) -> None:
        self.messages = messages_resource


def _patch_claude(monkeypatch, text: str, stop_reason: str = "end_turn") -> _FakeMessagesResource:
    fake_messages = _FakeMessagesResource(text, stop_reason)

    def _factory(api_key=None):  # noqa: ARG001
        return _FakeAnthropicClient(fake_messages)

    monkeypatch.setattr(claude_client_module.anthropic, "Anthropic", _factory)
    return fake_messages


# 8-Byte-PNG-Signatur reicht fuer die Magic-Byte-Pruefung (looks_like_plausible_content) -
# das Bild wird in Tests nie tatsaechlich dekodiert, da der Claude-Aufruf gemockt ist.
_MINIMAL_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"kein-echtes-png-dahinter"

_VALID_ANALYSIS_RESPONSE = (
    "<ocr_text>\nTransaktion VA02\nBeleg 12345\n</ocr_text>\n"
    "<analyse>\nScreenshot zeigt die SAP-Transaktion VA02 mit Beleg 12345 im Aenderungsmodus.\n</analyse>"
)


def _create_project(client) -> int:
    return client.post("/api/projects", json={"name": "Bild-Testprojekt"}).json()["id"]


def _upload_image(client, project_id: int, typ: str = "notiz") -> dict:
    return client.post(
        f"/api/projects/{project_id}/documents/upload",
        files={"file": ("screenshot.png", _MINIMAL_PNG_BYTES, "image/png")},
        data={"typ": typ},
    ).json()


def test_image_upload_reaches_review_required_with_parsed_analysis(client, monkeypatch):
    _patch_claude(monkeypatch, _VALID_ANALYSIS_RESPONSE)
    project_id = _create_project(client)

    # typ=meeting geschickt, muss serverseitig auf 'bild' ueberschrieben werden
    # (siehe document_service.create_uploaded_document).
    created = _upload_image(client, project_id, typ="meeting")
    assert created["status"] == "pending"
    assert created["typ"] == "bild"

    body = wait_for_document_status(
        client, project_id, created["id"], extra_terminal=("review_required",)
    )
    assert body["status"] == "review_required"
    assert body["inhalt"] is None
    assert "VA02" in body["ocr_text"]
    assert "VA02" in body["ki_analyse_rohtext"]
    assert body["dokumentdatum"] is not None


def test_image_analysis_with_unparseable_response_falls_back_gracefully(client, monkeypatch):
    _patch_claude(monkeypatch, "Ich sehe hier einfach einen Screenshot ohne festes Format.")
    project_id = _create_project(client)

    created = _upload_image(client, project_id)
    body = wait_for_document_status(
        client, project_id, created["id"], extra_terminal=("review_required",)
    )
    assert body["status"] == "review_required"
    assert body["ocr_text"] is None
    assert "Screenshot" in body["ki_analyse_rohtext"]


def test_confirming_review_indexes_document_and_makes_it_searchable(client, monkeypatch, app):
    _patch_claude(monkeypatch, _VALID_ANALYSIS_RESPONSE)
    project_id = _create_project(client)

    created = _upload_image(client, project_id)
    reviewed = wait_for_document_status(
        client, project_id, created["id"], extra_terminal=("review_required",)
    )
    assert reviewed["status"] == "review_required"

    confirm = client.post(
        f"/api/projects/{project_id}/documents/{created['id']}/review",
        json={"inhalt": reviewed["ki_analyse_rohtext"]},
    )
    assert confirm.status_code == 200
    # Regressionsschutz: die Bestaetigung muss sofort auf 'pending' wechseln
    # (wie reprocess_document), nicht auf 'review_required' stehen bleiben -
    # sonst haelt das Frontend das Dokument faelschlich fuer "wartet nicht auf
    # aktive Verarbeitung" und pollt den Abschluss der Hintergrund-Indexierung
    # nie nach (siehe Bugfix: Nutzer sah ein veraltetes Review-Panel, obwohl
    # das Dokument laengst 'ready' war, und ein zweiter Bestaetigungsversuch
    # schlug dann mit 409 fehl).
    assert confirm.json()["status"] == "pending"

    final = wait_for_document_status(client, project_id, created["id"])
    assert final["status"] == "ready"
    assert final["inhalt"] == reviewed["ki_analyse_rohtext"]
    # Rohdaten der urspruenglichen KI-Ausgabe bleiben unveraendert erhalten.
    assert final["ocr_text"] == reviewed["ocr_text"]
    assert final["ki_analyse_rohtext"] == reviewed["ki_analyse_rohtext"]

    from app.db.models.chunk import Chunk

    with app.state.session_factory() as db:
        chunks = db.query(Chunk).filter(Chunk.document_id == final["id"]).all()
    assert len(chunks) >= 1

    retrieval = client.post(
        f"/api/projects/{project_id}/retrieval-test",
        json={"query": "Welche SAP-Transaktion zeigt der Screenshot?", "top_k": 5},
    )
    assert retrieval.status_code == 200
    hits = retrieval.json()
    assert any(hit["document_id"] == final["id"] for hit in hits)


def test_confirming_review_with_edited_text_uses_edited_version(client, monkeypatch):
    _patch_claude(monkeypatch, _VALID_ANALYSIS_RESPONSE)
    project_id = _create_project(client)

    created = _upload_image(client, project_id)
    wait_for_document_status(client, project_id, created["id"], extra_terminal=("review_required",))

    edited_text = "Vom Nutzer korrigierte Fassung: Transaktion VA02, Beleg 99999."
    confirm = client.post(
        f"/api/projects/{project_id}/documents/{created['id']}/review",
        json={"inhalt": edited_text},
    )
    assert confirm.status_code == 200

    final = wait_for_document_status(client, project_id, created["id"])
    assert final["status"] == "ready"
    assert final["inhalt"] == edited_text


def test_review_rejects_document_not_in_review_required_status(client):
    project_id = _create_project(client)
    doc = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": "Text", "inhalt": "Ein ganz normaler Text."},
    ).json()
    wait_for_document_status(client, project_id, doc["id"])

    response = client.post(
        f"/api/projects/{project_id}/documents/{doc['id']}/review",
        json={"inhalt": "Versuch"},
    )
    assert response.status_code == 409


def test_review_rejects_empty_inhalt(client, monkeypatch):
    _patch_claude(monkeypatch, _VALID_ANALYSIS_RESPONSE)
    project_id = _create_project(client)

    created = _upload_image(client, project_id)
    wait_for_document_status(client, project_id, created["id"], extra_terminal=("review_required",))

    response = client.post(
        f"/api/projects/{project_id}/documents/{created['id']}/review",
        json={"inhalt": "   "},
    )
    assert response.status_code == 422


def test_image_analysis_failure_marks_document_failed(client, monkeypatch):
    from app.config import get_settings

    project_id = _create_project(client)
    # Siehe test_chat.py::test_user_message_survives_claude_failure: leerer
    # String statt delenv, damit ein evtl. in backend/.env hinterlegter echter
    # Key nicht als Fallback einspringt und einen echten API-Aufruf ausloest.
    monkeypatch.setenv("CLAUDE_API_KEY", "")
    get_settings.cache_clear()

    created = _upload_image(client, project_id)
    body = wait_for_document_status(client, project_id, created["id"])
    assert body["status"] == "failed"
    assert body["fehlermeldung"]
    get_settings.cache_clear()
