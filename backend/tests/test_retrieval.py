def _create_project(client, name: str) -> int:
    return client.post("/api/projects", json={"name": name}).json()["id"]


def _create_document(client, project_id: int, titel: str, inhalt: str) -> dict:
    return client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": titel, "inhalt": inhalt},
    ).json()


def test_retrieval_finds_semantically_relevant_chunk(client):
    project_id = _create_project(client, "Retrieval-Test")
    _create_document(
        client,
        project_id,
        "Berechtigungen",
        "Das SAP-Berechtigungskonzept regelt, welche Rolle auf welche Transaktion zugreifen darf.",
    )
    _create_document(
        client,
        project_id,
        "Kueche",
        "Die neue Kaffeemaschine im Buero steht im dritten Stock neben dem Kuehlschrank.",
    )

    response = client.post(
        f"/api/projects/{project_id}/retrieval-test",
        json={"query": "Wer darf auf welche SAP-Transaktion zugreifen?", "top_k": 5},
    )

    assert response.status_code == 200
    hits = response.json()
    assert len(hits) >= 1
    assert hits[0]["document_titel"] == "Berechtigungen"
    assert hits[0]["vector_rank"] == 1
    assert 0.0 <= hits[0]["vector_score"] <= 1.0


def test_retrieval_is_isolated_between_projects(client):
    project_a = _create_project(client, "Projekt A")
    project_b = _create_project(client, "Projekt B")

    _create_document(client, project_a, "Nur in A", "Ein ganz eindeutiger Satz nur fuer Projekt A.")

    response = client.post(
        f"/api/projects/{project_b}/retrieval-test",
        json={"query": "eindeutiger Satz", "top_k": 5},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_retrieval_on_empty_project_returns_empty_list(client):
    project_id = _create_project(client, "Leeres Projekt")

    response = client.post(
        f"/api/projects/{project_id}/retrieval-test",
        json={"query": "irgendetwas", "top_k": 5},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_retrieval_for_unknown_project_returns_404(client):
    response = client.post(
        "/api/projects/999999/retrieval-test",
        json={"query": "irgendetwas", "top_k": 5},
    )
    assert response.status_code == 404
