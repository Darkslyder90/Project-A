from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.indexing.chroma_client import get_chroma_client, get_or_create_collection
from app.indexing.index_metadata_service import get_index_metadata
from app.ingestion.embedding.embedder import get_embedder


@dataclass
class VectorSearchHit:
    chunk_id: str
    document_id: int
    vector_rank: int
    vector_score: float  # Cosine-Similarity (1 - Distanz), hoeher = aehnlicher


def vector_search(db: Session, project_id: int, query_text: str, top_k: int) -> list[VectorSearchHit]:
    """Reine Vektorsuche (Embeddings + Chroma) - der Keyword-Anteil des Hybrid
    Retrieval (SQLite FTS5) kommt erst in einem spaeteren Schritt dazu (siehe
    Briefing Punkt 7/10). Liefert nur Kern-Metadaten aus Chroma; vollstaendige
    Chunk-Metadaten (Text, Abschnitt, Dokumenttyp, ...) leben in SQLite und
    werden vom Aufrufer nachgeladen (siehe services/retrieval_service.py).

    Filtert zwingend auf project_id UND die aktuell aktive index_version (siehe
    Briefing: Projektisolation im Retrieval, auch waehrend einer spaeteren
    Neuindexierung im Hintergrund).
    """
    index_meta = get_index_metadata(db, project_id)
    if index_meta.active_index_version == 0 or not index_meta.active_collection_name:
        return []

    embedder = get_embedder(index_meta.active_embedding_model_name)
    query_vector = embedder.embed_query(query_text)

    settings = get_settings()
    client = get_chroma_client(str(settings.chroma_dir))
    collection = get_or_create_collection(client, index_meta.active_collection_name)

    result = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        where={
            "$and": [
                {"project_id": project_id},
                {"index_version": index_meta.active_index_version},
            ]
        },
    )

    ids = result["ids"][0] if result["ids"] else []
    distances = result["distances"][0] if result["distances"] else []
    metadatas = result["metadatas"][0] if result["metadatas"] else []

    hits: list[VectorSearchHit] = []
    for rank, (chunk_id, distance, metadata) in enumerate(zip(ids, distances, metadatas), start=1):
        hits.append(
            VectorSearchHit(
                chunk_id=chunk_id,
                document_id=metadata["document_id"],
                vector_rank=rank,
                vector_score=1 - distance,
            )
        )
    return hits
