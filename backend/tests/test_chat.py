from app.chat import claude_client as claude_client_module
from tests.helpers import wait_for_document_status


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeUsage:
    def __init__(self) -> None:
        self.input_tokens = 111
        self.output_tokens = 22


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


def _create_project_with_doc(client) -> int:
    project_id = client.post("/api/projects", json={"name": "Chat-Testprojekt"}).json()["id"]
    doc = client.post(
        f"/api/projects/{project_id}/documents",
        json={
            "typ": "notiz",
            "titel": "Ansprechpartner",
            "inhalt": "Der SAP-Support-Ansprechpartner fuer VA02-Probleme ist Frau Weber.",
        },
    ).json()
    # Seit Schritt 8 laeuft die Indexierung asynchron - der Chat braucht das
    # Dokument aber bereits durchsuchbar (fuer die Quellen-Zuordnung [S1]).
    wait_for_document_status(client, project_id, doc["id"])
    return project_id


def _create_conversation(client, project_id: int) -> int:
    return client.post(f"/api/projects/{project_id}/chat/conversations").json()["id"]


def test_create_and_list_conversations(client):
    project_id = _create_project_with_doc(client)

    created = client.post(f"/api/projects/{project_id}/chat/conversations")
    assert created.status_code == 201
    assert created.json()["titel"] is None

    listed = client.get(f"/api/projects/{project_id}/chat/conversations")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_send_message_persists_both_turns_and_sets_title(client, monkeypatch):
    project_id = _create_project_with_doc(client)
    conversation_id = _create_conversation(client, project_id)
    _patch_claude(monkeypatch, "Der Ansprechpartner ist Frau Weber [S1].")

    response = client.post(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}/messages",
        json={"query": "Wer ist der Ansprechpartner fuer VA02?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nachricht"]["rolle"] == "assistant"
    assert body["nachricht"]["text"] == "Der Ansprechpartner ist Frau Weber [S1]."
    assert len(body["nachricht"]["quellen"]) == 1
    assert body["nachricht"]["quellen"][0]["source_id"] == "S1"
    assert body["conversation"]["titel"] == "Wer ist der Ansprechpartner fuer VA02?"

    detail = client.get(f"/api/projects/{project_id}/chat/conversations/{conversation_id}").json()
    assert len(detail["nachrichten"]) == 2
    assert detail["nachrichten"][0]["rolle"] == "user"
    assert detail["nachrichten"][1]["rolle"] == "assistant"


def test_second_message_sends_history_to_claude(client, monkeypatch):
    project_id = _create_project_with_doc(client)
    conversation_id = _create_conversation(client, project_id)
    fake_messages = _patch_claude(monkeypatch, "Erste Antwort.")

    client.post(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}/messages",
        json={"query": "Erste Frage"},
    )

    fake_messages._text = "Zweite Antwort."
    client.post(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}/messages",
        json={"query": "Zweite Frage"},
    )

    sent = fake_messages.last_messages
    assert sent[0] == {"role": "user", "content": "Erste Frage"}
    assert sent[1] == {"role": "assistant", "content": "Erste Antwort."}
    assert sent[2] == {"role": "user", "content": "Zweite Frage"}


def test_send_message_handles_refusal_gracefully(client, monkeypatch):
    project_id = _create_project_with_doc(client)
    conversation_id = _create_conversation(client, project_id)
    _patch_claude(monkeypatch, "", stop_reason="refusal")

    response = client.post(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}/messages",
        json={"query": "Frage?"},
    )

    assert response.status_code == 200
    assert response.json()["nachricht"]["quellen"] is None
    assert "nicht beantworten" in response.json()["nachricht"]["text"]


def test_user_message_survives_claude_failure(client, monkeypatch):
    from app.config import get_settings

    project_id = _create_project_with_doc(client)
    conversation_id = _create_conversation(client, project_id)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    get_settings.cache_clear()

    response = client.post(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}/messages",
        json={"query": "Wird diese Frage gespeichert?"},
    )
    assert response.status_code == 503
    get_settings.cache_clear()

    detail = client.get(f"/api/projects/{project_id}/chat/conversations/{conversation_id}").json()
    assert len(detail["nachrichten"]) == 1
    assert detail["nachrichten"][0]["rolle"] == "user"
    assert detail["nachrichten"][0]["text"] == "Wird diese Frage gespeichert?"


def test_rename_and_delete_conversation(client):
    project_id = _create_project_with_doc(client)
    conversation_id = _create_conversation(client, project_id)

    renamed = client.patch(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}",
        json={"titel": "Mein Titel"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["titel"] == "Mein Titel"

    deleted = client.delete(f"/api/projects/{project_id}/chat/conversations/{conversation_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/projects/{project_id}/chat/conversations/{conversation_id}").status_code == 404


def test_conversations_are_isolated_between_projects(client):
    project_a = _create_project_with_doc(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]

    conversation_id = _create_conversation(client, project_a)

    assert client.get(f"/api/projects/{project_b}/chat/conversations/{conversation_id}").status_code == 404
    assert len(client.get(f"/api/projects/{project_b}/chat/conversations").json()) == 0


def test_deleted_document_shows_as_geloescht_in_source_snapshot(client, app, monkeypatch):
    project_id = _create_project_with_doc(client)
    conversation_id = _create_conversation(client, project_id)
    _patch_claude(monkeypatch, "Laut [S1] ist Frau Weber zustaendig.")

    client.post(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}/messages",
        json={"query": "Wer ist zustaendig?"},
    )

    # Dokument nur aus SQLite entfernen (simuliert eine spaetere Loeschung),
    # ohne die Konversation anzufassen - der Snapshot muss trotzdem lesbar bleiben.
    from app.db.models.document import Document

    with app.state.session_factory() as db:
        doc = db.query(Document).first()
        db.delete(doc)
        db.commit()

    detail = client.get(f"/api/projects/{project_id}/chat/conversations/{conversation_id}").json()
    assistant_message = detail["nachrichten"][1]
    assert assistant_message["quellen"][0]["geloescht"] is True
