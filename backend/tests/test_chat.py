from app.chat import claude_client as claude_client_module


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

    def create(self, *, model, max_tokens, system, messages):  # noqa: ARG002
        return _FakeMessage(self._text, self._stop_reason, model)


class _FakeAnthropicClient:
    def __init__(self, text: str, stop_reason: str) -> None:
        self.messages = _FakeMessagesResource(text, stop_reason)


def _patch_claude(monkeypatch, text: str, stop_reason: str = "end_turn") -> None:
    def _factory(api_key=None):  # noqa: ARG001
        return _FakeAnthropicClient(text, stop_reason)

    monkeypatch.setattr(claude_client_module.anthropic, "Anthropic", _factory)


def _create_project_with_doc(client) -> int:
    project_id = client.post("/api/projects", json={"name": "Chat-Testprojekt"}).json()["id"]
    client.post(
        f"/api/projects/{project_id}/documents",
        json={
            "typ": "notiz",
            "titel": "Ansprechpartner",
            "inhalt": "Der SAP-Support-Ansprechpartner fuer VA02-Probleme ist Frau Weber.",
        },
    )
    return project_id


def test_chat_answer_cites_valid_source(client, monkeypatch):
    project_id = _create_project_with_doc(client)
    _patch_claude(monkeypatch, "Der Ansprechpartner ist Frau Weber [S1].")

    response = client.post(
        f"/api/projects/{project_id}/chat", json={"query": "Wer ist Ansprechpartner?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["antwort"] == "Der Ansprechpartner ist Frau Weber [S1]."
    assert len(body["quellen"]) == 1
    assert body["quellen"][0]["source_id"] == "S1"
    assert body["quellen"][0]["document_titel"] == "Ansprechpartner"
    assert body["unbekannte_zitate"] == []


def test_chat_flags_invalid_citation_without_crashing(client, monkeypatch):
    project_id = _create_project_with_doc(client)
    _patch_claude(monkeypatch, "Laut [S1] und [S99] ist das so.")

    response = client.post(f"/api/projects/{project_id}/chat", json={"query": "Frage?"})

    assert response.status_code == 200
    body = response.json()
    assert body["unbekannte_zitate"] == ["S99"]
    assert all(q["source_id"] != "S99" for q in body["quellen"])


def test_chat_handles_refusal_gracefully(client, monkeypatch):
    project_id = _create_project_with_doc(client)
    _patch_claude(monkeypatch, "", stop_reason="refusal")

    response = client.post(f"/api/projects/{project_id}/chat", json={"query": "Frage?"})

    assert response.status_code == 200
    body = response.json()
    assert body["quellen"] == []
    assert "nicht beantworten" in body["antwort"]


def test_chat_logs_api_usage(client, app, monkeypatch):
    from app.db.models.api_usage_log import ApiUsageLog

    project_id = _create_project_with_doc(client)
    _patch_claude(monkeypatch, "Antwort ohne Zitat.")

    client.post(f"/api/projects/{project_id}/chat", json={"query": "Frage?"})

    with app.state.session_factory() as db:
        logs = db.query(ApiUsageLog).filter(ApiUsageLog.project_id == project_id).all()
    assert len(logs) == 1
    assert logs[0].zweck.value == "chat"
    assert logs[0].erfolg is True
    assert logs[0].input_tokens == 111
    assert logs[0].output_tokens == 22


def test_chat_for_unknown_project_returns_404(client, monkeypatch):
    _patch_claude(monkeypatch, "irrelevant")
    response = client.post("/api/projects/999999/chat", json={"query": "Frage?"})
    assert response.status_code == 404


def test_chat_without_api_key_returns_503(client, monkeypatch):
    from app.config import get_settings

    project_id = _create_project_with_doc(client)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    get_settings.cache_clear()

    response = client.post(f"/api/projects/{project_id}/chat", json={"query": "Frage?"})

    assert response.status_code == 503
    get_settings.cache_clear()
