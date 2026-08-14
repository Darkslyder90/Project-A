from tests.helpers import wait_for_document_status


def _create_project(client) -> int:
    return client.post("/api/projects", json={"name": "Task-Testprojekt"}).json()["id"]


def _create_person(client, project_id: int, name: str = "Anna Weber") -> dict:
    return client.post(f"/api/projects/{project_id}/people", json={"name": name}).json()


def _create_ready_document(client, project_id: int, titel: str = "Doku") -> dict:
    created = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": titel, "inhalt": "Ein kurzer Text."},
    ).json()
    return wait_for_document_status(client, project_id, created["id"])


def test_create_task_with_assignment_and_documents(client):
    project_id = _create_project(client)
    person = _create_person(client, project_id)
    doc = _create_ready_document(client, project_id)

    created = client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "titel": "Berechtigungskonzept pruefen",
            "zugewiesen_an": person["id"],
            "faellig_am": "2026-09-01",
            "dokument_ids": [doc["id"]],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "offen"
    assert body["zugewiesen_an"] == person["id"]
    assert body["dokument_ids"] == [doc["id"]]


def test_create_task_rejects_person_from_other_project(client):
    project_a = _create_project(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]
    person_b = _create_person(client, project_b)

    response = client.post(
        f"/api/projects/{project_a}/tasks",
        json={"titel": "X", "zugewiesen_an": person_b["id"]},
    )
    assert response.status_code == 422


def test_create_task_rejects_document_from_other_project(client):
    project_a = _create_project(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]
    doc_b = _create_ready_document(client, project_b)

    response = client.post(
        f"/api/projects/{project_a}/tasks",
        json={"titel": "X", "dokument_ids": [doc_b["id"]]},
    )
    assert response.status_code == 404


def test_update_task_status_and_unassign(client):
    project_id = _create_project(client)
    person = _create_person(client, project_id)
    task = client.post(
        f"/api/projects/{project_id}/tasks",
        json={"titel": "T", "zugewiesen_an": person["id"]},
    ).json()

    in_arbeit = client.patch(
        f"/api/projects/{project_id}/tasks/{task['id']}", json={"status": "in_arbeit"}
    )
    assert in_arbeit.status_code == 200
    assert in_arbeit.json()["status"] == "in_arbeit"
    assert in_arbeit.json()["zugewiesen_an"] == person["id"]  # unveraendert, da nicht im Patch enthalten

    unassigned = client.patch(
        f"/api/projects/{project_id}/tasks/{task['id']}", json={"zugewiesen_an": None}
    )
    assert unassigned.status_code == 200
    assert unassigned.json()["zugewiesen_an"] is None


def test_filter_tasks_by_status(client):
    project_id = _create_project(client)
    client.post(f"/api/projects/{project_id}/tasks", json={"titel": "Offen"})
    erledigt = client.post(
        f"/api/projects/{project_id}/tasks", json={"titel": "Erledigt", "status": "erledigt"}
    ).json()
    client.patch(f"/api/projects/{project_id}/tasks/{erledigt['id']}", json={"status": "erledigt"})

    response = client.get(f"/api/projects/{project_id}/tasks", params={"status_filter": "erledigt"})
    assert response.status_code == 200
    titles = [t["titel"] for t in response.json()]
    assert titles == ["Erledigt"]


def test_link_and_unlink_document(client):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    task = client.post(f"/api/projects/{project_id}/tasks", json={"titel": "T"}).json()
    assert task["dokument_ids"] == []

    linked = client.post(f"/api/projects/{project_id}/tasks/{task['id']}/documents/{doc['id']}")
    assert linked.status_code == 200
    assert linked.json()["dokument_ids"] == [doc["id"]]

    # Erneutes Verknuepfen ist idempotent, kein Duplikat/Fehler.
    linked_again = client.post(f"/api/projects/{project_id}/tasks/{task['id']}/documents/{doc['id']}")
    assert linked_again.status_code == 200
    assert linked_again.json()["dokument_ids"] == [doc["id"]]

    unlinked = client.request(
        "DELETE", f"/api/projects/{project_id}/tasks/{task['id']}/documents/{doc['id']}"
    )
    assert unlinked.status_code == 200
    assert unlinked.json()["dokument_ids"] == []


def test_deleting_task_removes_document_links_but_not_document(client, app):
    from app.db.models.task import TaskDocument

    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    task = client.post(
        f"/api/projects/{project_id}/tasks", json={"titel": "T", "dokument_ids": [doc["id"]]}
    ).json()

    assert client.delete(f"/api/projects/{project_id}/tasks/{task['id']}").status_code == 204

    with app.state.session_factory() as db:
        assert db.query(TaskDocument).count() == 0

    assert client.get(f"/api/projects/{project_id}/documents/{doc['id']}").status_code == 200


def test_tasks_are_isolated_between_projects(client):
    project_a = _create_project(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]

    task = client.post(f"/api/projects/{project_a}/tasks", json={"titel": "Nur in A"}).json()

    assert client.get(f"/api/projects/{project_b}/tasks/{task['id']}").status_code == 404
    assert client.get(f"/api/projects/{project_b}/tasks").json() == []


def test_task_for_unknown_project_returns_404(client):
    response = client.post("/api/projects/999999/tasks", json={"titel": "X"})
    assert response.status_code == 404
