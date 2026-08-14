from sqlalchemy.orm import Session

from app.chat.prompt_builder import PromptSource
from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.retrieval.hybrid_search import hybrid_search


def build_sources(db: Session, project_id: int, query: str) -> list[PromptSource]:
    """Fuehrt die Hybrid-Retrieval-Anfrage (Vektor + Keyword/FTS5 + RRF-Fusion,
    siehe Schritt 10) fuer eine Chat-Frage aus und baut daraus die
    serverseitigen PromptSource-Objekte (S1..Sn), die Claude als abgegrenzten
    <dokumente>-Block sieht. candidate_k/final_k kommen aus den globalen
    RAG-Settings (siehe retrieval/hybrid_search.py).
    """
    hits = hybrid_search(db, project_id, query)
    if not hits:
        return []

    chunk_ids = [h.chunk_id for h in hits]
    chunks_by_id = {c.id: c for c in db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()}

    document_ids = {h.document_id for h in hits}
    titles_by_document_id = {
        d.id: d.titel for d in db.query(Document).filter(Document.id.in_(document_ids)).all()
    }

    sources: list[PromptSource] = []
    for i, hit in enumerate(hits):
        chunk = chunks_by_id.get(hit.chunk_id)
        if chunk is None:
            continue
        sources.append(
            PromptSource(
                source_id=f"S{i + 1}",
                chunk_id=chunk.id,
                document_id=hit.document_id,
                document_titel=titles_by_document_id.get(hit.document_id, "(unbekannt)"),
                dokumentdatum=chunk.dokumentdatum,
                abschnitt=chunk.abschnitt,
                text=chunk.text,
            )
        )
    return sources
