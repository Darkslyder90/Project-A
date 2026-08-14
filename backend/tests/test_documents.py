from app.db.models.chunk import Chunk
from app.db.models.index_metadata import IndexMetadata
from app.indexing.chroma_client import get_chroma_client, get_or_create_collection
from tests.helpers import wait_for_document_status


def _create_project(client) -> int:
    return client.post("/api/projects", json={"name": "Doku-Testprojekt"}).json()["id"]


def test_create_manual_document_becomes_ready_and_is_chunked(client, app):
    project_id = _create_project(client)

    response = client.post(
        f"/api/projects/{project_id}/documents",
        json={
            "typ": "notiz",
            "titel": "Erste Notiz",
            "inhalt": "Dies ist eine kurze Testnotiz ueber das SAP-Customizing in Transaktion VA02.",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "pending"  # Verarbeitung laeuft asynchron im Hintergrund (Schritt 8)

    body = wait_for_document_status(client, project_id, created["id"])
    assert body["status"] == "ready"
    assert body["fehlermeldung"] is None

    with app.state.session_factory() as db:
        chunks = db.query(Chunk).filter(Chunk.document_id == body["id"]).all()
        assert len(chunks) >= 1
        assert chunks[0].text != ""
        assert chunks[0].dokumenttyp == "notiz"

        index_meta = db.get(IndexMetadata, project_id)
        assert index_meta.active_index_version == 1
        assert index_meta.active_collection_name == f"project_{project_id}_v1"
        assert index_meta.active_embedding_model_name == "intfloat/multilingual-e5-base"

    settings = app.state.settings
    chroma_client = get_chroma_client(str(settings.chroma_dir))
    collection = get_or_create_collection(chroma_client, f"project_{project_id}_v1")
    assert collection.count() == len(chunks)


def test_reprocessing_document_does_not_duplicate_chunks(client, app):
    project_id = _create_project(client)
    doc = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": "N", "inhalt": "Ein Satz zum Testen der Idempotenz."},
    ).json()
    wait_for_document_status(client, project_id, doc["id"])

    with app.state.session_factory() as db:
        first_count = db.query(Chunk).filter(Chunk.document_id == doc["id"]).count()

    reprocessed = client.post(f"/api/projects/{project_id}/documents/{doc['id']}/reprocess")
    assert reprocessed.status_code == 200
    assert reprocessed.json()["status"] == "pending"

    body = wait_for_document_status(client, project_id, doc["id"])
    assert body["status"] == "ready"

    with app.state.session_factory() as db:
        second_count = db.query(Chunk).filter(Chunk.document_id == doc["id"]).count()

    assert first_count == second_count

    settings = app.state.settings
    chroma_client = get_chroma_client(str(settings.chroma_dir))
    collection = get_or_create_collection(chroma_client, f"project_{project_id}_v1")
    assert collection.count() == second_count


def test_two_documents_in_same_project_share_index_version(client, app):
    project_id = _create_project(client)
    doc1 = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": "N1", "inhalt": "Erster Text."},
    ).json()
    doc2 = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": "N2", "inhalt": "Zweiter Text."},
    ).json()
    wait_for_document_status(client, project_id, doc1["id"])
    wait_for_document_status(client, project_id, doc2["id"])

    with app.state.session_factory() as db:
        versions = {c.index_version for c in db.query(Chunk).all()}
    assert versions == {1}


def test_documents_are_isolated_between_projects(client, app):
    project_a = _create_project(client)
    project_b = client.post("/api/projects", json={"name": "Anderes Projekt"}).json()["id"]

    doc_a = client.post(
        f"/api/projects/{project_a}/documents",
        json={"typ": "notiz", "titel": "Nur in A", "inhalt": "Inhalt A"},
    ).json()

    assert client.get(f"/api/projects/{project_b}/documents/{doc_a['id']}").status_code == 404
    assert len(client.get(f"/api/projects/{project_b}/documents").json()) == 0
    assert len(client.get(f"/api/projects/{project_a}/documents").json()) == 1


def test_create_document_for_unknown_project_returns_404(client):
    response = client.post(
        "/api/projects/999999/documents",
        json={"typ": "notiz", "titel": "X", "inhalt": "Y"},
    )
    assert response.status_code == 404


def test_empty_content_is_rejected_by_schema_validation(client):
    project_id = _create_project(client)
    response = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": "Leer", "inhalt": ""},
    )
    assert response.status_code == 422  # Pydantic min_length=1


def test_deleting_project_also_removes_its_chroma_collection(client, app):
    project_id = _create_project(client)
    doc = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": "N", "inhalt": "Text, der embedded wird."},
    ).json()
    wait_for_document_status(client, project_id, doc["id"])

    settings = app.state.settings
    chroma_client = get_chroma_client(str(settings.chroma_dir))
    collection_name = f"project_{project_id}_v1"
    assert collection_name in [c.name for c in chroma_client.list_collections()]

    assert client.delete(f"/api/projects/{project_id}").status_code == 204

    assert collection_name not in [c.name for c in chroma_client.list_collections()]


def test_deleting_document_removes_chunks_chroma_and_file(client, app):
    from app.db.models.document import Document
    from app.retrieval.keyword_search import keyword_search

    project_id = _create_project(client)
    upload = client.post(
        f"/api/projects/{project_id}/documents/upload",
        files={"file": ("notiz.txt", b"Ein einzigartiger Begriff KANTALUPE55 im Text.", "text/plain")},
        data={"typ": "notiz"},
    ).json()
    doc = wait_for_document_status(client, project_id, upload["id"])
    assert doc["status"] == "ready"

    settings = app.state.settings
    with app.state.session_factory() as db:
        original_dateipfad = db.get(Document, doc["id"]).original_dateipfad
    file_path = settings.uploads_dir / original_dateipfad
    assert file_path.is_file()

    response = client.delete(f"/api/projects/{project_id}/documents/{doc['id']}")
    assert response.status_code == 204

    assert client.get(f"/api/projects/{project_id}/documents/{doc['id']}").status_code == 404
    assert doc["id"] not in [d["id"] for d in client.get(f"/api/projects/{project_id}/documents").json()]
    assert not file_path.exists()

    with app.state.session_factory() as db:
        assert db.query(Chunk).filter(Chunk.document_id == doc["id"]).count() == 0
        assert keyword_search(db, project_id, "KANTALUPE55", top_k=5) == []

    chroma_client = get_chroma_client(str(settings.chroma_dir))
    collection = get_or_create_collection(chroma_client, f"project_{project_id}_v1")
    assert collection.get(where={"document_id": doc["id"]})["ids"] == []


def test_deleting_document_removes_only_task_link_not_the_task(client, app):
    from app.db.models.task import TaskDocument

    project_id = _create_project(client)
    doc = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": "N", "inhalt": "Text."},
    ).json()
    wait_for_document_status(client, project_id, doc["id"])
    task = client.post(
        f"/api/projects/{project_id}/tasks", json={"titel": "T", "dokument_ids": [doc["id"]]}
    ).json()
    assert task["dokument_ids"] == [doc["id"]]

    assert client.delete(f"/api/projects/{project_id}/documents/{doc['id']}").status_code == 204

    task_after = client.get(f"/api/projects/{project_id}/tasks/{task['id']}").json()
    assert task_after["dokument_ids"] == []
    with app.state.session_factory() as db:
        assert db.query(TaskDocument).count() == 0


def test_deleting_unknown_document_returns_404(client):
    project_id = _create_project(client)
    assert client.delete(f"/api/projects/{project_id}/documents/999999").status_code == 404


def test_whitespace_only_content_marks_document_failed_not_500(client):
    # Einzelnes Leerzeichen erfuellt min_length=1 (Schema-Ebene), ist aber nach
    # .strip() leer - muss von der Pipeline als "failed" abgefangen werden,
    # nicht als 500er crashen (siehe Briefing: Fehlertoleranz).
    project_id = _create_project(client)
    created = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": "Leer", "inhalt": " "},
    ).json()

    body = wait_for_document_status(client, project_id, created["id"])
    assert body["status"] == "failed"
    assert "kein indexierbarer inhalt" in body["fehlermeldung"].lower()
