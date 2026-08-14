from tests.helpers import wait_for_document_status


def _create_project(client) -> int:
    return client.post("/api/projects", json={"name": "Meeting-Testprojekt"}).json()["id"]


def _create_person(client, project_id: int, name: str = "Anna Weber") -> dict:
    return client.post(f"/api/projects/{project_id}/people", json={"name": name}).json()


def _create_ready_document(client, project_id: int, titel: str = "Protokoll") -> dict:
    created = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "meeting", "titel": titel, "inhalt": "Teilnehmer besprachen X und Y."},
    ).json()
    return wait_for_document_status(client, project_id, created["id"])


def test_create_meeting_with_participants(client):
    project_id = _create_project(client)
    person = _create_person(client, project_id)
    doc = _create_ready_document(client, project_id)

    created = client.post(
        f"/api/projects/{project_id}/meetings",
        json={
            "datum": "2026-08-01",
            "document_id": doc["id"],
            "zusammenfassung": "Kickoff besprochen.",
            "teilnehmer_ids": [person["id"]],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["document_id"] == doc["id"]
    assert body["teilnehmer_ids"] == [person["id"]]


def test_create_meeting_without_document(client):
    project_id = _create_project(client)

    created = client.post(
        f"/api/projects/{project_id}/meetings",
        json={"datum": "2026-08-01", "zusammenfassung": "Nur Notizen, kein Protokoll."},
    )
    assert created.status_code == 201
    assert created.json()["document_id"] is None


def test_attach_document_to_meeting_via_update(client):
    project_id = _create_project(client)
    meeting = client.post(
        f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-01"}
    ).json()
    doc = _create_ready_document(client, project_id)

    updated = client.patch(
        f"/api/projects/{project_id}/meetings/{meeting['id']}", json={"document_id": doc["id"]}
    )
    assert updated.status_code == 200
    assert updated.json()["document_id"] == doc["id"]


def test_update_meeting_rejects_document_already_used_by_another_meeting(client):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    client.post(f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-01", "document_id": doc["id"]})
    other_meeting = client.post(f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-02"}).json()

    response = client.patch(
        f"/api/projects/{project_id}/meetings/{other_meeting['id']}", json={"document_id": doc["id"]}
    )
    assert response.status_code == 409


def test_deleting_meeting_without_document_does_not_error(client):
    project_id = _create_project(client)
    meeting = client.post(
        f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-01"}
    ).json()

    assert client.delete(f"/api/projects/{project_id}/meetings/{meeting['id']}").status_code == 204
    assert client.get(f"/api/projects/{project_id}/meetings/{meeting['id']}").status_code == 404


def test_create_meeting_rejects_document_from_other_project(client):
    project_a = _create_project(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]
    doc_b = _create_ready_document(client, project_b)

    response = client.post(
        f"/api/projects/{project_a}/meetings",
        json={"datum": "2026-08-01", "document_id": doc_b["id"]},
    )
    assert response.status_code == 404


def test_create_meeting_rejects_document_already_used_by_another_meeting(client):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)

    first = client.post(
        f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-01", "document_id": doc["id"]}
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-02", "document_id": doc["id"]}
    )
    assert second.status_code == 409


def test_create_meeting_rejects_participant_from_other_project(client):
    project_a = _create_project(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]
    person_b = _create_person(client, project_b)
    doc_a = _create_ready_document(client, project_a)

    response = client.post(
        f"/api/projects/{project_a}/meetings",
        json={"datum": "2026-08-01", "document_id": doc_a["id"], "teilnehmer_ids": [person_b["id"]]},
    )
    assert response.status_code == 422


def test_add_and_remove_participant(client):
    project_id = _create_project(client)
    person = _create_person(client, project_id)
    doc = _create_ready_document(client, project_id)
    meeting = client.post(
        f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-01", "document_id": doc["id"]}
    ).json()
    assert meeting["teilnehmer_ids"] == []

    added = client.post(f"/api/projects/{project_id}/meetings/{meeting['id']}/participants/{person['id']}")
    assert added.status_code == 200
    assert added.json()["teilnehmer_ids"] == [person["id"]]

    removed = client.request(
        "DELETE", f"/api/projects/{project_id}/meetings/{meeting['id']}/participants/{person['id']}"
    )
    assert removed.status_code == 200
    assert removed.json()["teilnehmer_ids"] == []


def test_update_meeting_datum_and_zusammenfassung(client):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    meeting = client.post(
        f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-01", "document_id": doc["id"]}
    ).json()

    updated = client.patch(
        f"/api/projects/{project_id}/meetings/{meeting['id']}",
        json={"datum": "2026-08-05", "zusammenfassung": "Nachtrag."},
    )
    assert updated.status_code == 200
    assert updated.json()["datum"] == "2026-08-05"
    assert updated.json()["zusammenfassung"] == "Nachtrag."


def test_document_of_meeting_cannot_be_deleted_directly(client):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    meeting = client.post(
        f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-01", "document_id": doc["id"]}
    ).json()

    response = client.delete(f"/api/projects/{project_id}/documents/{doc['id']}")
    assert response.status_code == 409
    assert str(meeting["id"]) in response.json()["detail"]


def test_deleting_meeting_also_deletes_its_document(client):
    project_id = _create_project(client)
    doc = _create_ready_document(client, project_id)
    meeting = client.post(
        f"/api/projects/{project_id}/meetings", json={"datum": "2026-08-01", "document_id": doc["id"]}
    ).json()

    deleted = client.delete(f"/api/projects/{project_id}/meetings/{meeting['id']}")
    assert deleted.status_code == 204

    assert client.get(f"/api/projects/{project_id}/meetings/{meeting['id']}").status_code == 404
    assert client.get(f"/api/projects/{project_id}/documents/{doc['id']}").status_code == 404


def test_meetings_are_isolated_between_projects(client):
    project_a = _create_project(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]
    doc = _create_ready_document(client, project_a)
    meeting = client.post(
        f"/api/projects/{project_a}/meetings", json={"datum": "2026-08-01", "document_id": doc["id"]}
    ).json()

    assert client.get(f"/api/projects/{project_b}/meetings/{meeting['id']}").status_code == 404
    assert client.get(f"/api/projects/{project_b}/meetings").json() == []


def test_meeting_for_unknown_project_returns_404(client):
    response = client.post(
        "/api/projects/999999/meetings", json={"datum": "2026-08-01", "document_id": 1}
    )
    assert response.status_code == 404
