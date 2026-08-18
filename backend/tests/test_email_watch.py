from datetime import UTC, datetime, timedelta

from app.db.models.document import Document
from app.services import email_oauth_service, email_watch_service, ms_graph_client
from app.services.ms_graph_client import GraphMessage, GraphTokens
from tests.helpers import wait_for_document_status


def _create_project(client) -> int:
    return client.post("/api/projects", json={"name": "Mail-Testprojekt"}).json()["id"]


def _fake_message(message_id: str, subject: str, body: str, received_am: datetime, sender: str = "kollege@kunde.de"):
    return GraphMessage(
        id=message_id, subject=subject, received_am=received_am, sender=sender, plaintext_body=body
    )


# --- EmailWatchConfig CRUD -----------------------------------------------


def test_email_watch_config_crud_roundtrip(client):
    project_id = _create_project(client)

    assert client.get(f"/api/projects/{project_id}/email-watch-config").json() is None

    created = client.put(
        f"/api/projects/{project_id}/email-watch-config",
        json={
            "outlook_ordner_id": "folder-1",
            "outlook_ordner_name": "SAP-Projekt",
            "aktiv": True,
            "polling_intervall_minuten": 15,
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["outlook_ordner_id"] == "folder-1"
    assert body["polling_intervall_minuten"] == 15
    assert body["letzte_abfrage_am"] is None
    assert body["letzter_fehler"] is None

    fetched = client.get(f"/api/projects/{project_id}/email-watch-config").json()
    assert fetched["outlook_ordner_name"] == "SAP-Projekt"

    updated = client.put(
        f"/api/projects/{project_id}/email-watch-config",
        json={
            "outlook_ordner_id": "folder-1",
            "outlook_ordner_name": "SAP-Projekt (umbenannt)",
            "aktiv": False,
            "polling_intervall_minuten": 30,
        },
    ).json()
    assert updated["outlook_ordner_name"] == "SAP-Projekt (umbenannt)"
    assert updated["aktiv"] is False

    assert client.delete(f"/api/projects/{project_id}/email-watch-config").status_code == 204
    assert client.get(f"/api/projects/{project_id}/email-watch-config").json() is None


def test_email_watch_config_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999999/email-watch-config")
    assert response.status_code == 404


def test_poll_now_without_config_returns_404(client):
    project_id = _create_project(client)
    response = client.post(f"/api/projects/{project_id}/email-watch-config/poll-now")
    assert response.status_code == 404


# --- OAuth-Endpunkte (ohne echte Azure-Registrierung) ---------------------


def test_oauth_login_without_ms_graph_config_returns_clear_error(client):
    response = client.get("/api/email-watch/oauth/login")
    assert response.status_code == 422
    assert "MS_GRAPH" in response.json()["detail"]


def test_oauth_status_when_not_connected(client):
    response = client.get("/api/email-watch/oauth/status")
    assert response.status_code == 200
    assert response.json() == {"connected": False, "account_email": None, "access_token_expires_am": None}


def test_folders_without_connected_account_returns_clear_error(client):
    response = client.get("/api/email-watch/folders")
    assert response.status_code == 422


# --- email_oauth_service: Verschluesselung/Refresh -------------------------


def test_store_and_retrieve_tokens_roundtrip(app):
    with app.state.session_factory() as db:
        tokens = GraphTokens(
            access_token="access-123",
            refresh_token="refresh-456",
            expires_am=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
        )
        email_oauth_service._store_tokens(db, tokens, account_email="ich@firma.de")

        assert email_oauth_service.is_connected(db) is True
        assert email_oauth_service.get_valid_access_token(db) == "access-123"


def test_get_valid_access_token_refreshes_when_close_to_expiry(app, monkeypatch):
    with app.state.session_factory() as db:
        expiring_soon = GraphTokens(
            access_token="old-access",
            refresh_token="refresh-456",
            expires_am=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=1),
        )
        email_oauth_service._store_tokens(db, expiring_soon)

        refreshed = GraphTokens(
            access_token="new-access",
            refresh_token="new-refresh",
            expires_am=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
        )
        monkeypatch.setattr(ms_graph_client, "refresh_tokens", lambda settings, refresh_token: refreshed)

        assert email_oauth_service.get_valid_access_token(db) == "new-access"


def test_disconnect_clears_stored_tokens(app):
    with app.state.session_factory() as db:
        tokens = GraphTokens(
            access_token="a", refresh_token="r", expires_am=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
        )
        email_oauth_service._store_tokens(db, tokens)
        assert email_oauth_service.is_connected(db) is True

        email_oauth_service.disconnect(db)
        assert email_oauth_service.is_connected(db) is False


# --- email_watch_service.poll_one: Ingestion, Dedup, Cutoff, Fehler --------


def _connect_fake_account(db) -> None:
    tokens = GraphTokens(
        access_token="access-token",
        refresh_token="refresh-token",
        expires_am=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
    )
    email_oauth_service._store_tokens(db, tokens)


def test_poll_one_creates_documents_from_new_mails(client, app, monkeypatch):
    project_id = _create_project(client)
    now = datetime.now(UTC).replace(tzinfo=None)

    with app.state.session_factory() as db:
        _connect_fake_account(db)
        config = email_watch_service.upsert_config(
            db,
            project_id,
            outlook_ordner_id="folder-1",
            outlook_ordner_name="SAP-Projekt",
            aktiv=True,
            polling_intervall_minuten=10,
        )

        messages = [
            _fake_message("msg-1", "Frage zu VA02", "Bitte um Rueckmeldung.", now - timedelta(hours=1)),
            _fake_message("msg-2", "Termin naechste Woche", "Passt Dienstag?", now - timedelta(hours=2)),
        ]
        monkeypatch.setattr(ms_graph_client, "fetch_messages_since", lambda *a, **kw: messages)

        email_watch_service.poll_one(db, config, app.state.task_runner)

        created = db.query(Document).filter(Document.project_id == project_id).all()
        assert {d.outlook_message_id for d in created} == {"msg-1", "msg-2"}
        assert all(d.typ.value == "email" for d in created)
        assert config.letzter_fehler is None
        assert config.letzte_abfrage_am is not None
        document_ids = [d.id for d in created]

    for document_id in document_ids:
        wait_for_document_status(client, project_id, document_id)


def test_poll_one_does_not_duplicate_already_seen_mails(client, app, monkeypatch):
    project_id = _create_project(client)
    now = datetime.now(UTC).replace(tzinfo=None)

    with app.state.session_factory() as db:
        _connect_fake_account(db)
        config = email_watch_service.upsert_config(
            db, project_id, outlook_ordner_id="folder-1", outlook_ordner_name="SAP-Projekt",
            aktiv=True, polling_intervall_minuten=10,
        )
        message = _fake_message("msg-dup", "Betreff", "Text", now - timedelta(hours=1))
        monkeypatch.setattr(ms_graph_client, "fetch_messages_since", lambda *a, **kw: [message])

        email_watch_service.poll_one(db, config, app.state.task_runner)
        email_watch_service.poll_one(db, config, app.state.task_runner)

        created = db.query(Document).filter(Document.project_id == project_id).all()
        assert len(created) == 1
        document_id = created[0].id

    wait_for_document_status(client, project_id, document_id)


def test_poll_one_skips_mails_older_than_one_week(client, app, monkeypatch):
    project_id = _create_project(client)
    now = datetime.now(UTC).replace(tzinfo=None)

    with app.state.session_factory() as db:
        _connect_fake_account(db)
        config = email_watch_service.upsert_config(
            db, project_id, outlook_ordner_id="folder-1", outlook_ordner_name="SAP-Projekt",
            aktiv=True, polling_intervall_minuten=10,
        )
        old_message = _fake_message("msg-old", "Alt", "Text", now - timedelta(days=10))
        monkeypatch.setattr(ms_graph_client, "fetch_messages_since", lambda *a, **kw: [old_message])

        email_watch_service.poll_one(db, config, app.state.task_runner)

        created = db.query(Document).filter(Document.project_id == project_id).all()
        assert created == []


def test_poll_one_records_error_without_crashing(client, app, monkeypatch):
    project_id = _create_project(client)

    with app.state.session_factory() as db:
        config = email_watch_service.upsert_config(
            db, project_id, outlook_ordner_id="folder-1", outlook_ordner_name="SAP-Projekt",
            aktiv=True, polling_intervall_minuten=10,
        )
        # Kein verbundenes Konto -> get_valid_access_token wirft GraphApiError.
        email_watch_service.poll_one(db, config, app.state.task_runner)

        db.refresh(config)
        assert config.letzter_fehler is not None
        assert "Microsoft-Konto" in config.letzter_fehler


def test_poll_due_configs_only_polls_active_and_due_configs(client, app, monkeypatch):
    project_a = _create_project(client)
    project_b = _create_project(client)
    now = datetime.now(UTC).replace(tzinfo=None)

    with app.state.session_factory() as db:
        _connect_fake_account(db)
        # a: aktiv, noch nie abgefragt -> faellig
        email_watch_service.upsert_config(
            db, project_a, outlook_ordner_id="f-a", outlook_ordner_name="A",
            aktiv=True, polling_intervall_minuten=10,
        )
        # b: inaktiv -> nie faellig, unabhaengig vom Intervall
        config_b = email_watch_service.upsert_config(
            db, project_b, outlook_ordner_id="f-b", outlook_ordner_name="B",
            aktiv=False, polling_intervall_minuten=10,
        )

        polled_projects: list[int] = []

        def _fake_fetch(access_token, folder_id, since):
            polled_projects.append(folder_id)
            return []

        monkeypatch.setattr(ms_graph_client, "fetch_messages_since", _fake_fetch)

        email_watch_service.poll_due_configs(db, app.state.task_runner)

        assert polled_projects == ["f-a"]
        db.refresh(config_b)
        assert config_b.letzte_abfrage_am is None
