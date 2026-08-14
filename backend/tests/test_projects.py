from app.db.models.index_metadata import IndexMetadata


def test_create_project_also_creates_index_metadata(client, app):
    response = client.post("/api/projects", json={"name": "Kundenprojekt A", "beschreibung": "Test"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Kundenprojekt A"
    assert body["beschreibung"] == "Test"
    assert "id" in body

    with app.state.session_factory() as db:
        index_meta = db.get(IndexMetadata, body["id"])
        assert index_meta is not None
        assert index_meta.active_index_version == 0


def test_list_projects_returns_all_created_projects(client):
    client.post("/api/projects", json={"name": "Projekt 1"})
    client.post("/api/projects", json={"name": "Projekt 2"})

    response = client.get("/api/projects")
    assert response.status_code == 200
    names = {p["name"] for p in response.json()}
    assert {"Projekt 1", "Projekt 2"}.issubset(names)


def test_get_unknown_project_returns_404(client):
    response = client.get("/api/projects/999999")
    assert response.status_code == 404


def test_update_project_can_clear_description(client):
    created = client.post("/api/projects", json={"name": "P", "beschreibung": "Alt"}).json()

    response = client.patch(f"/api/projects/{created['id']}", json={"beschreibung": None})
    assert response.status_code == 200
    assert response.json()["beschreibung"] is None
    assert response.json()["name"] == "P"  # unveraendert, da nicht im Payload


def test_delete_project_removes_it_and_is_isolated_from_others(client):
    p1 = client.post("/api/projects", json={"name": "Zu loeschen"}).json()
    p2 = client.post("/api/projects", json={"name": "Bleibt bestehen"}).json()

    delete_response = client.delete(f"/api/projects/{p1['id']}")
    assert delete_response.status_code == 204

    assert client.get(f"/api/projects/{p1['id']}").status_code == 404
    assert client.get(f"/api/projects/{p2['id']}").status_code == 200

    # Erneutes Loeschen (bereits geloescht) darf nicht crashen (idempotente
    # Cleanup-Strategie, siehe Briefing) - hier via 404, da die Ressource weg ist.
    assert client.delete(f"/api/projects/{p1['id']}").status_code == 404
