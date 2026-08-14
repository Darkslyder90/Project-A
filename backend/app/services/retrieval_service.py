from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.retrieval.vector_search import vector_search
from app.services.project_service import get_project


@dataclass
class RetrievalTestHit:
    chunk_id: str
    document_id: int
    document_titel: str
    vector_rank: int
    vector_score: float
    text: str
    dokumenttyp: str | None
    dokumentdatum: date | None
    abschnitt: str | None


def test_retrieval(db: Session, project_id: int, query: str, top_k: int) -> list[RetrievalTestHit]:
    """Debug-/Testfunktion fuer Schritt 4 ("Retrieval-Test ohne Claude"): fuehrt
    nur die Vektorsuche aus und reichert die Treffer mit den vollstaendigen
    Chunk-/Document-Metadaten aus SQLite an - ohne einen Claude-Aufruf.
    """
    get_project(db, project_id)  # 404, falls Projekt nicht existiert

    hits = vector_search(db, project_id, query, top_k)
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
            # Sollte nie vorkommen (Chroma und SQLite werden gemeinsam
            # geschrieben) - defensiv trotzdem ueberspringen statt zu crashen.
            continue
        results.append(
            RetrievalTestHit(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                document_titel=titles_by_document_id.get(hit.document_id, "(unbekannt)"),
                vector_rank=hit.vector_rank,
                vector_score=hit.vector_score,
                text=chunk.text,
                dokumenttyp=chunk.dokumenttyp,
                dokumentdatum=chunk.dokumentdatum,
                abschnitt=chunk.abschnitt,
            )
        )
    return results
