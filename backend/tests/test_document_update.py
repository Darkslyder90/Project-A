from app.db.models.chunk import Chunk
from tests.helpers import wait_for_document_status


def _create_project(client) -> int:
    return client.post("/api/projects", json={"name": "Update-Testprojekt"}).json()["id"]


def _create_ready_document(client, project_id: int, **overrides) -> dict:
    payload = {"typ": "notiz", "titel": "Original", "inhalt": "Ein Text ueber SAP VA02."}
    payload.update(overrides)
    created = client.post(f"/api/projects/{project_id}/documents", json=payload).json()
    return wait_for_document_status(client, project_id, created["id"])


def test_update_titel_is_trivial_and_does_not_reindex(client, app):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    with app.state.session_factory() as db:
        chunk_ids_before = {c.id for c in db.query(Chunk).filter(Chunk.document_id == doc["id"]).all()}

    updated = client.patch(f"/api/projects/{project_id}/documents/{doc['id']}", json={"titel": "Neuer Titel"})
    assert updated.status_code == 200
    body = updated.json()
    assert body["titel"] == "Neuer Titel"
    assert body["status"] == "ready"  # kein Reindex ausgeloest

    with app.state.session_factory() as db:
        chunk_ids_after = {c.id for c in db.query(Chunk).filter(Chunk.document_id == doc["id"]).all()}
    assert chunk_ids_after == chunk_ids_before


def test_update_dokumentdatum_updates_denormalized_chunk_field(client, app):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)

    updated = client.patch(
        f"/api/projects/{project_id}/documents/{doc['id']}", json={"dokumentdatum": "2020-01-01"}
    )
    assert updated.status_code == 200
    assert updated.json()["dokumentdatum"] == "2020-01-01"
    assert updated.json()["status"] == "ready"

    with app.state.session_factory() as db:
        chunks = db.query(Chunk).filter(Chunk.document_id == doc["id"]).all()
        assert all(str(c.dokumentdatum) == "2020-01-01" for c in chunks)


def test_update_typ_updates_denormalized_chunk_field(client, app):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)

    updated = client.patch(f"/api/projects/{project_id}/documents/{doc['id']}", json={"typ": "prozess"})
    assert updated.status_code == 200
    assert updated.json()["typ"] == "prozess"

    with app.state.session_factory() as db:
        chunks = db.query(Chunk).filter(Chunk.document_id == doc["id"]).all()
        assert all(c.dokumenttyp == "prozess" for c in chunks)


def test_update_inhalt_triggers_full_reindex(client, app):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    with app.state.session_factory() as db:
        chunk_ids_before = {c.id for c in db.query(Chunk).filter(Chunk.document_id == doc["id"]).all()}

    updated = client.patch(
        f"/api/projects/{project_id}/documents/{doc['id']}",
        json={"inhalt": "Ein komplett anderer Text ueber Berechtigungskonzepte."},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "pending"  # asynchron neu eingeplant

    final = wait_for_document_status(client, project_id, doc["id"])
    assert final["status"] == "ready"
    assert final["inhalt"] == "Ein komplett anderer Text ueber Berechtigungskonzepte."

    with app.state.session_factory() as db:
        chunk_ids_after = {c.id for c in db.query(Chunk).filter(Chunk.document_id == doc["id"]).all()}
    assert chunk_ids_after.isdisjoint(chunk_ids_before)
    assert len(chunk_ids_after) >= 1


def test_update_inhalt_with_unchanged_value_does_not_reindex(client, app):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    with app.state.session_factory() as db:
        chunk_ids_before = {c.id for c in db.query(Chunk).filter(Chunk.document_id == doc["id"]).all()}

    updated = client.patch(
        f"/api/projects/{project_id}/documents/{doc['id']}", json={"inhalt": doc["inhalt"]}
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "ready"

    with app.state.session_factory() as db:
        chunk_ids_after = {c.id for c in db.query(Chunk).filter(Chunk.document_id == doc["id"]).all()}
    assert chunk_ids_after == chunk_ids_before


def test_update_with_empty_body_changes_nothing(client):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)

    updated = client.patch(f"/api/projects/{project_id}/documents/{doc['id']}", json={})
    assert updated.status_code == 200
    assert updated.json()["titel"] == doc["titel"]
    assert updated.json()["inhalt"] == doc["inhalt"]
    assert updated.json()["status"] == "ready"


def test_update_unknown_document_returns_404(client):
    project_id = _create_project(client)
    response = client.patch(f"/api/projects/{project_id}/documents/999999", json={"titel": "X"})
    assert response.status_code == 404


def test_update_is_isolated_between_projects(client):
    project_a = _create_project(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]
    doc = _create_ready_document(client, project_a)

    response = client.patch(f"/api/projects/{project_b}/documents/{doc['id']}", json={"titel": "X"})
    assert response.status_code == 404
