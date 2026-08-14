from tests.helpers import wait_for_document_status


def _create_project(client) -> int:
    return client.post("/api/projects", json={"name": "Tag-Testprojekt"}).json()["id"]


def _create_ready_document(client, project_id: int, titel: str = "Doku") -> dict:
    created = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": titel, "inhalt": "Ein kurzer Text."},
    ).json()
    return wait_for_document_status(client, project_id, created["id"])


def test_assigning_tag_creates_it_and_links_document(client):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    assert doc["tag_ids"] == []

    response = client.post(f"/api/projects/{project_id}/documents/{doc['id']}/tags", json={"name": "Kickoff"})
    assert response.status_code == 200
    updated = response.json()
    assert len(updated["tag_ids"]) == 1

    tags = client.get(f"/api/projects/{project_id}/tags").json()
    assert [t["name"] for t in tags] == ["Kickoff"]
    assert tags[0]["id"] == updated["tag_ids"][0]


def test_assigning_same_tag_name_twice_reuses_the_tag(client):
    project_id = _create_project(client)
    doc1 = _create_ready_document(client, project_id, "Doc1")
    doc2 = _create_ready_document(client, project_id, "Doc2")

    client.post(f"/api/projects/{project_id}/documents/{doc1['id']}/tags", json={"name": "Wichtig"})
    client.post(f"/api/projects/{project_id}/documents/{doc2['id']}/tags", json={"name": "Wichtig"})

    tags = client.get(f"/api/projects/{project_id}/tags").json()
    assert len(tags) == 1  # kein Duplikat, derselbe Tag wiederverwendet

    # Erneutes Zuweisen desselben Tags an dasselbe Dokument ist idempotent.
    again = client.post(f"/api/projects/{project_id}/documents/{doc1['id']}/tags", json={"name": "Wichtig"})
    assert len(again.json()["tag_ids"]) == 1


def test_unassign_tag_removes_link_but_not_the_tag_itself(client):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    assigned = client.post(
        f"/api/projects/{project_id}/documents/{doc['id']}/tags", json={"name": "Temp"}
    ).json()
    tag_id = assigned["tag_ids"][0]

    unassigned = client.request(
        "DELETE", f"/api/projects/{project_id}/documents/{doc['id']}/tags/{tag_id}"
    )
    assert unassigned.status_code == 200
    assert unassigned.json()["tag_ids"] == []

    tags = client.get(f"/api/projects/{project_id}/tags").json()
    assert len(tags) == 1  # Tag bleibt im Projekt bestehen


def test_deleting_tag_removes_it_from_all_documents(client):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    assigned = client.post(
        f"/api/projects/{project_id}/documents/{doc['id']}/tags", json={"name": "Zu loeschen"}
    ).json()
    tag_id = assigned["tag_ids"][0]

    assert client.delete(f"/api/projects/{project_id}/tags/{tag_id}").status_code == 204

    doc_after = client.get(f"/api/projects/{project_id}/documents/{doc['id']}").json()
    assert doc_after["tag_ids"] == []
    assert client.get(f"/api/projects/{project_id}/tags").json() == []


def test_deleting_document_removes_tag_links(client, app):
    from app.db.models.document import DocumentTag

    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    client.post(f"/api/projects/{project_id}/documents/{doc['id']}/tags", json={"name": "X"})

    assert client.delete(f"/api/projects/{project_id}/documents/{doc['id']}").status_code == 204

    with app.state.session_factory() as db:
        assert db.query(DocumentTag).count() == 0
    # Der Tag selbst bleibt im Projekt bestehen (nur die Verknuepfung faellt weg).
    tags = client.get(f"/api/projects/{project_id}/tags").json()
    assert len(tags) == 1


def test_tags_are_isolated_between_projects(client):
    project_a = _create_project(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]
    doc_a = _create_ready_document(client, project_a)

    client.post(f"/api/projects/{project_a}/documents/{doc_a['id']}/tags", json={"name": "Nur A"})

    assert client.get(f"/api/projects/{project_b}/tags").json() == []


def test_tag_for_unknown_project_returns_404(client):
    response = client.get("/api/projects/999999/tags")
    assert response.status_code == 404
