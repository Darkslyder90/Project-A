from app.retrieval.fusion import FusedHit, reciprocal_rank_fusion
from app.retrieval.keyword_search import KeywordSearchHit, _build_match_query, keyword_search
from app.retrieval.reranker import rerank
from app.retrieval.vector_search import VectorSearchHit
from tests.helpers import wait_for_document_status


def _create_project(client, name: str) -> int:
    return client.post("/api/projects", json={"name": name}).json()["id"]


def _create_document(client, project_id: int, titel: str, inhalt: str) -> dict:
    created = client.post(
        f"/api/projects/{project_id}/documents",
        json={"typ": "notiz", "titel": titel, "inhalt": inhalt},
    ).json()
    return wait_for_document_status(client, project_id, created["id"])


# --- Reine Unit-Tests fuer Fusion/Rerank/Query-Building (deterministisch, ohne DB/Embedding) ---


def test_reciprocal_rank_fusion_combines_and_ranks_by_rrf_score():
    vector_hits = [
        VectorSearchHit(chunk_id="a", document_id=1, vector_rank=1, vector_score=0.9),
        VectorSearchHit(chunk_id="b", document_id=2, vector_rank=2, vector_score=0.5),
    ]
    keyword_hits = [
        KeywordSearchHit(chunk_id="b", document_id=2, keyword_rank=1, keyword_score=-5.0),
        KeywordSearchHit(chunk_id="c", document_id=3, keyword_rank=2, keyword_score=-2.0),
    ]

    fused = reciprocal_rank_fusion(vector_hits, keyword_hits)
    by_id = {f.chunk_id: f for f in fused}

    assert by_id["b"].gefunden_ueber == "beide"
    assert by_id["a"].gefunden_ueber == "vector"
    assert by_id["c"].gefunden_ueber == "keyword"

    # "b" ist in beiden Pfaden vertreten (Rang 2 vector + Rang 1 keyword) und
    # bekommt dadurch einen hoeheren RRF-Score als "a" (nur Rang 1 vector allein).
    assert by_id["b"].fusion_score > by_id["a"].fusion_score
    assert fused[0].chunk_id == "b"
    assert [f.fusion_rank for f in fused] == [1, 2, 3]


def test_reciprocal_rank_fusion_with_empty_keyword_hits_keeps_vector_order():
    vector_hits = [
        VectorSearchHit(chunk_id="x", document_id=1, vector_rank=1, vector_score=0.8),
        VectorSearchHit(chunk_id="y", document_id=1, vector_rank=2, vector_score=0.4),
    ]
    fused = reciprocal_rank_fusion(vector_hits, [])
    assert [f.chunk_id for f in fused] == ["x", "y"]
    assert all(f.gefunden_ueber == "vector" for f in fused)


def test_passthrough_reranker_returns_input_unchanged():
    hits = [
        FusedHit(
            chunk_id="a",
            document_id=1,
            vector_rank=1,
            keyword_rank=None,
            vector_score=0.9,
            keyword_score=None,
            fusion_score=0.1,
            fusion_rank=1,
            gefunden_ueber="vector",
        )
    ]
    assert rerank(hits, "irgendeine Anfrage") == hits


def test_build_match_query_quotes_each_token_and_joins_with_or():
    assert _build_match_query("VA02 Beleg-12345") == '"VA02" OR "Beleg" OR "12345"'


def test_build_match_query_returns_none_for_query_without_word_characters():
    assert _build_match_query("???") is None


# --- Integrationstests ueber den echten Retrieval-Test-Endpunkt ---


def test_retrieval_test_hit_found_via_both_paths_is_marked_beide(client):
    project_id = _create_project(client, "Hybrid-Test")
    _create_document(
        client,
        project_id,
        "Berechtigungen",
        "Das SAP-Berechtigungskonzept regelt, welche Rolle auf welche Transaktion VA02 zugreifen darf.",
    )
    _create_document(
        client,
        project_id,
        "Kueche",
        "Die neue Kaffeemaschine im Buero steht im dritten Stock neben dem Kuehlschrank.",
    )

    response = client.post(
        f"/api/projects/{project_id}/retrieval-test",
        json={"query": "Wer darf auf welche SAP-Transaktion VA02 zugreifen?", "top_k": 5},
    )
    assert response.status_code == 200
    hits = response.json()
    assert len(hits) >= 1
    top = hits[0]
    assert top["document_titel"] == "Berechtigungen"
    assert top["fusion_rank"] == 1
    assert top["gefunden_ueber"] == "beide"
    assert top["vector_rank"] is not None
    assert top["keyword_rank"] is not None


def test_keyword_path_is_isolated_between_projects(client):
    project_a = _create_project(client, "Projekt A")
    project_b = _create_project(client, "Projekt B")

    _create_document(
        client, project_a, "Ticket", "Ticketnummer INC0099887 betrifft einen Fehler im Modul MM."
    )

    response_wrong_project = client.post(
        f"/api/projects/{project_b}/retrieval-test", json={"query": "INC0099887", "top_k": 5}
    )
    assert response_wrong_project.json() == []

    response_correct_project = client.post(
        f"/api/projects/{project_a}/retrieval-test", json={"query": "INC0099887", "top_k": 5}
    )
    hits = response_correct_project.json()
    assert len(hits) == 1
    assert hits[0]["keyword_rank"] == 1


def test_keyword_search_filters_by_active_index_version(client, app):
    from app.db.models.chunk import Chunk
    from app.db.models.index_metadata import IndexMetadata

    project_id = _create_project(client, "Version-Test")
    doc = _create_document(client, project_id, "Notiz", "Ein Text mit dem Suchbegriff ZIRKON9000 darin.")

    with app.state.session_factory() as db:
        meta = db.get(IndexMetadata, project_id)
        assert meta.active_index_version == 1

        # Simuliert einen Chunk einer noch nicht aktiven pending_index_version
        # (z. B. waehrend eines spaeteren Rebuilds, siehe Briefing) - darf trotz
        # gleichem Suchbegriff NICHT ins Keyword-Retrieval einfliessen.
        pending_chunk = Chunk(
            id="pending-chunk-1",
            document_id=doc["id"],
            index_version=2,
            chunk_index=0,
            text="Ein Text mit dem Suchbegriff ZIRKON9000 darin (pending Version).",
        )
        db.add(pending_chunk)
        db.commit()

        hits = keyword_search(db, project_id, "ZIRKON9000", top_k=10)
        assert len(hits) == 1
        assert hits[0].chunk_id != "pending-chunk-1"


def test_reprocessing_document_does_not_leave_orphaned_fts_entries(client, app):
    project_id = _create_project(client, "Reindex-Test")
    doc = _create_document(client, project_id, "Notiz", "Ein einzigartiger Begriff LAPISLAZULI77 im Text.")

    with app.state.session_factory() as db:
        hits_before = keyword_search(db, project_id, "LAPISLAZULI77", top_k=5)
        assert len(hits_before) == 1
        old_chunk_id = hits_before[0].chunk_id

    reprocessed = client.post(f"/api/projects/{project_id}/documents/{doc['id']}/reprocess")
    assert reprocessed.status_code == 200
    wait_for_document_status(client, project_id, doc["id"])

    with app.state.session_factory() as db:
        hits_after = keyword_search(db, project_id, "LAPISLAZULI77", top_k=5)
        assert len(hits_after) == 1
        assert hits_after[0].chunk_id != old_chunk_id
