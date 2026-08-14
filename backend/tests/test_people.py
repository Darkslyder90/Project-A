def _create_project(client) -> int:
    return client.post("/api/projects", json={"name": "Personen-Testprojekt"}).json()["id"]


def _create_person(client, project_id: int, name: str = "Anna Weber", **kwargs) -> dict:
    payload = {"name": name, **kwargs}
    return client.post(f"/api/projects/{project_id}/people", json=payload).json()


def test_create_and_list_people(client):
    project_id = _create_project(client)

    created = client.post(
        f"/api/projects/{project_id}/people",
        json={"name": "Anna Weber", "rolle": "SAP-Beraterin", "kontaktinfo": "anna@example.com"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Anna Weber"
    assert body["rolle"] == "SAP-Beraterin"

    listed = client.get(f"/api/projects/{project_id}/people")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_update_person_partial(client):
    project_id = _create_project(client)
    person = _create_person(client, project_id, rolle="Alt")

    updated = client.patch(f"/api/projects/{project_id}/people/{person['id']}", json={"rolle": "Neu"})
    assert updated.status_code == 200
    assert updated.json()["rolle"] == "Neu"
    assert updated.json()["name"] == person["name"]  # unveraendert


def test_delete_person_unassigns_tasks_and_removes_meeting_links(client):
    project_id = _create_project(client)
    person = _create_person(client, project_id)

    task = client.post(
        f"/api/projects/{project_id}/tasks",
        json={"titel": "Kickoff vorbereiten", "zugewiesen_an": person["id"]},
    ).json()

    doc = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "meeting", "titel": "Kickoff-Protokoll", "inhalt": "Text."},
    ).json()
    meeting = client.post(
        f"/api/projects/{project_id}/meetings",
        json={"datum": "2026-08-01", "document_id": doc["id"], "teilnehmer_ids": [person["id"]]},
    ).json()
    assert meeting["teilnehmer_ids"] == [person["id"]]

    deleted = client.delete(f"/api/projects/{project_id}/people/{person['id']}")
    assert deleted.status_code == 204

    # Task bleibt bestehen, nur die Zuweisung wird entfernt (siehe Briefing).
    task_after = client.get(f"/api/projects/{project_id}/tasks/{task['id']}").json()
    assert task_after["zugewiesen_an"] is None

    meeting_after = client.get(f"/api/projects/{project_id}/meetings/{meeting['id']}").json()
    assert meeting_after["teilnehmer_ids"] == []


def test_people_are_isolated_between_projects(client):
    project_a = _create_project(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]

    person = _create_person(client, project_a)

    assert client.get(f"/api/projects/{project_b}/people/{person['id']}").status_code == 404
    assert client.get(f"/api/projects/{project_b}/people").json() == []


def test_person_for_unknown_project_returns_404(client):
    response = client.post("/api/projects/999999/people", json={"name": "X"})
    assert response.status_code == 404
