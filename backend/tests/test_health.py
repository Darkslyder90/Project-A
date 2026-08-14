def test_health_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["data_dir"] == "ok"
    assert body["checks"]["uploads_dir"] == "ok"
    assert body["checks"]["chroma_dir"] == "ok"
    assert body["checks"]["backups_dir"] == "ok"


def test_health_never_calls_claude(client, monkeypatch):
    # Absicherung gegen versehentliche zukuenftige Kopplung: der Healthcheck darf
    # laut Briefing niemals einen Claude-API-Aufruf ausloesen. Kein echter Import
    # eines Claude-Clients irgendwo im health-Modul.
    import app.api.routes.health as health_module

    assert "anthropic" not in dir(health_module)
