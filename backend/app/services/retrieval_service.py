from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.retrieval.hybrid_search import hybrid_search
from app.services.project_service import get_project


@dataclass
class RetrievalTestHit:
    chunk_id: str
    document_id: int
    document_titel: str
    vector_rank: int | None
    vector_score: float | None
    keyword_rank: int | None
    keyword_score: float | None
    fusion_rank: int
    gefunden_ueber: str
    text: str
    dokumenttyp: str | None
    dokumentdatum: date | None
    abschnitt: str | None


def test_retrieval(db: Session, project_id: int, query: str, top_k: int) -> list[RetrievalTestHit]:
    """Debug-/Testfunktion fuer Schritt 4/10 ("Retrieval-Test ohne Claude"):
    fuehrt den vollstaendigen Hybrid-Retrieval-Ablauf aus (Vektor + Keyword/
    FTS5 + RRF-Fusion) und reichert die Treffer mit den vollstaendigen Chunk-/
    Document-Metadaten aus SQLite an - ohne einen Claude-Aufruf. `top_k`
    ueberschreibt dabei nur final_k fuer diese eine Debug-Anfrage
    (candidate_k_vector/candidate_k_keyword kommen unveraendert aus den
    globalen RAG-Settings, siehe retrieval/hybrid_search.py).
    """
    get_project(db, project_id)  # 404, falls Projekt nicht existiert

    hits = hybrid_search(db, project_id, query, final_k_override=top_k)
    if not hits:
        return []

    chunk_ids = [h.chunk_id for h in hits]
    chunks_by_id = {c.id: c for c in db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()}

    document_ids = {h.document_id for h in hits}
    titles_by_document_id = {
        d.id: d.titel for d in db.query(Document).filter(Document.id.in_(document_ids)).all()
    }

    results: list[RetrievalTestHit] = []
    for hit in hits:
        chunk = chunks_by_id.get(hit.chunk_id)
        if chunk is None:
            # Sollte nie vorkommen (Chroma/FTS5 und SQLite werden gemeinsam
            # geschrieben) - defensiv trotzdem ueberspringen statt zu crashen.
            continue
        results.append(
            RetrievalTestHit(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                document_titel=titles_by_document_id.get(hit.document_id, "(unbekannt)"),
                vector_rank=hit.vector_rank,
                vector_score=hit.vector_score,
                keyword_rank=hit.keyword_rank,
                keyword_score=hit.keyword_score,
                fusion_rank=hit.fusion_rank,
                gefunden_ueber=hit.gefunden_ueber,
                text=chunk.text,
                dokumenttyp=chunk.dokumenttyp,
                dokumentdatum=chunk.dokumentdatum,
                abschnitt=chunk.abschnitt,
            )
        )
    return results
