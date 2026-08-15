from app.chat import claude_client as claude_client_module


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeUsage:
    def __init__(self) -> None:
        self.input_tokens = 10
        self.output_tokens = 5


class _FakeMessage:
    def __init__(self, model: str) -> None:
        self.content = [_FakeTextBlock("Antwort.")]
        self.usage = _FakeUsage()
        self.stop_reason = "end_turn"
        self.model = model


class _FakeMessagesResource:
    def __init__(self) -> None:
        self.last_model: str | None = None

    def create(self, *, model, max_tokens, system, messages):  # noqa: ARG002
        self.last_model = model
        return _FakeMessage(model)


class _FakeAnthropicClient:
    def __init__(self, messages_resource: _FakeMessagesResource) -> None:
        self.messages = messages_resource


def _patch_claude(monkeypatch) -> _FakeMessagesResource:
    fake_messages = _FakeMessagesResource()

    def _factory(api_key=None):  # noqa: ARG001
        return _FakeAnthropicClient(fake_messages)

    monkeypatch.setattr(claude_client_module.anthropic, "Anthropic", _factory)
    return fake_messages


def test_get_settings_returns_defaults_with_env_fallback_key(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["claude_api_key_status"] == "env"  # conftest setzt CLAUDE_API_KEY
    assert body["claude_api_key_masked"] is not None
    assert body["claude_model"] is None
    assert body["effective_claude_model"] == "claude-opus-5"
    assert body["embedding_model_name"] == "intfloat/multilingual-e5-base"
    assert body["candidate_k_vector"] == 20
    assert body["final_k"] == 8


def test_patch_settings_stores_encrypted_key_and_updates_status(client):
    updated = client.patch("/api/settings", json={"claude_api_key": "sk-ant-mein-echter-key-123"})
    assert updated.status_code == 200
    body = updated.json()
    assert body["claude_api_key_status"] == "db"
    assert body["claude_api_key_masked"] is not None
    assert "sk-ant-mein-echter-key-123" not in updated.text  # Klartext darf nie zurueckkommen


def test_patch_settings_with_empty_key_clears_stored_key(client):
    client.patch("/api/settings", json={"claude_api_key": "sk-ant-temp"})
    cleared = client.patch("/api/settings", json={"claude_api_key": ""})
    assert cleared.status_code == 200
    assert cleared.json()["claude_api_key_status"] == "env"  # faellt zurueck auf .env-Fallback


def test_patch_settings_without_encryption_key_returns_clear_error(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    get_settings.cache_clear()

    response = client.patch("/api/settings", json={"claude_api_key": "sk-ant-x"})
    assert response.status_code == 422
    assert "SETTINGS_ENCRYPTION_KEY" in response.json()["detail"]
    get_settings.cache_clear()


def test_changed_encryption_secret_makes_stored_key_undecryptable(client, monkeypatch):
    from app.config import get_settings

    client.patch("/api/settings", json={"claude_api_key": "sk-ant-original"})

    from cryptography.fernet import Fernet

    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))
    get_settings.cache_clear()

    response = client.get("/api/settings")
    assert response.json()["claude_api_key_status"] == "db_invalid"
    assert response.json()["claude_api_key_masked"] is None
    get_settings.cache_clear()


def test_patch_settings_updates_rag_tuning_values(client):
    response = client.patch(
        "/api/settings",
        json={
            "candidate_k_vector": 15,
            "candidate_k_keyword": 12,
            "final_k": 6,
            "chunk_ziel_tokens": 300,
            "chunk_overlap_tokens": 40,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_k_vector"] == 15
    assert body["candidate_k_keyword"] == 12
    assert body["final_k"] == 6
    assert body["chunk_ziel_tokens"] == 300
    assert body["chunk_overlap_tokens"] == 40


def test_patch_settings_rejects_out_of_range_values(client):
    response = client.patch("/api/settings", json={"final_k": 0})
    assert response.status_code == 422


def test_chat_uses_configured_claude_model(client, monkeypatch):
    fake_messages = _patch_claude(monkeypatch)
    client.patch("/api/settings", json={"claude_model": "claude-sonnet-5"})

    project_id = client.post("/api/projects", json={"name": "Modell-Test"}).json()["id"]
    conversation_id = client.post(f"/api/projects/{project_id}/chat/conversations").json()["id"]

    response = client.post(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}/messages",
        json={"query": "Hallo?"},
    )
    assert response.status_code == 200
    assert fake_messages.last_model == "claude-sonnet-5"


def test_usage_summary_counts_todays_chat_call(client, monkeypatch):
    _patch_claude(monkeypatch)
    project_id = client.post("/api/projects", json={"name": "Usage-Test"}).json()["id"]
    conversation_id = client.post(f"/api/projects/{project_id}/chat/conversations").json()["id"]

    before = client.get("/api/settings/usage").json()
    client.post(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}/messages",
        json={"query": "Hallo?"},
    )
    after = client.get("/api/settings/usage").json()

    assert after["heute"]["anfragen"] == before["heute"]["anfragen"] + 1
    assert after["heute"]["tokens"] > before["heute"]["tokens"]
    assert after["woche"]["anfragen"] >= after["heute"]["anfragen"]
    assert after["monat"]["anfragen"] >= after["woche"]["anfragen"]
    # Kein Preis fuer "claude-opus-5" hinterlegt (Testdatenbank startet ohne
    # Seed-Daten, siehe Migration vs. Base.metadata.create_all in conftest.py).
    assert after["heute"]["vollstaendig"] is False
    assert after["heute"]["kosten_eur"] == 0.0


def test_get_settings_includes_default_wechselkurs(client):
    body = client.get("/api/settings").json()
    assert body["eur_usd_wechselkurs"] == 0.92


def test_patch_settings_updates_wechselkurs(client):
    response = client.patch("/api/settings", json={"eur_usd_wechselkurs": 1.1})
    assert response.status_code == 200
    assert response.json()["eur_usd_wechselkurs"] == 1.1


def test_patch_settings_rejects_non_positive_wechselkurs(client):
    response = client.patch("/api/settings", json={"eur_usd_wechselkurs": 0})
    assert response.status_code == 422


def test_create_list_delete_pricing(client):
    assert client.get("/api/settings/pricing").json() == []

    created = client.post(
        "/api/settings/pricing",
        json={
            "modell_name": "claude-opus-5",
            "gueltig_ab": "2026-01-01",
            "input_preis_pro_million_usd": 5.0,
            "output_preis_pro_million_usd": 25.0,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["modell_name"] == "claude-opus-5"
    assert body["cache_write_preis_pro_million_usd"] is None

    listed = client.get("/api/settings/pricing").json()
    assert len(listed) == 1

    deleted = client.delete(f"/api/settings/pricing/{body['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/settings/pricing").json() == []


def test_delete_unknown_pricing_returns_404(client):
    assert client.delete("/api/settings/pricing/999999").status_code == 404


def test_usage_summary_reflects_configured_pricing_and_wechselkurs(client, monkeypatch):
    _patch_claude(monkeypatch)
    client.post(
        "/api/settings/pricing",
        json={
            "modell_name": "claude-opus-5",
            "gueltig_ab": "2020-01-01",
            "input_preis_pro_million_usd": 5.0,
            "output_preis_pro_million_usd": 25.0,
        },
    )
    client.patch("/api/settings", json={"eur_usd_wechselkurs": 1.0})

    project_id = client.post("/api/projects", json={"name": "Kosten-Test"}).json()["id"]
    conversation_id = client.post(f"/api/projects/{project_id}/chat/conversations").json()["id"]
    client.post(
        f"/api/projects/{project_id}/chat/conversations/{conversation_id}/messages",
        json={"query": "Hallo?"},
    )

    usage = client.get("/api/settings/usage").json()
    assert usage["heute"]["vollstaendig"] is True
    assert usage["heute"]["kosten_eur"] > 0
