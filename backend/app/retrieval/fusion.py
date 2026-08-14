from dataclasses import dataclass

from app.retrieval.keyword_search import KeywordSearchHit
from app.retrieval.vector_search import VectorSearchHit

# Standard-RRF-Konstante (siehe Cormack et al. 2009) - die Fusion basiert
# ausschliesslich auf Raengen, nicht auf rohen Similarity-/BM25-Scores (siehe
# Briefing: "kein blindes 50/50 auf rohen Scores", da beide Skalen nicht
# vergleichbar sind).
_RRF_K = 60


@dataclass
class FusedHit:
    """Laufzeit-DTO (siehe Briefing RetrievedChunk/RetrievalResult) - nicht
    persistent, nur pro Anfrage erzeugt."""

    chunk_id: str
    document_id: int
    vector_rank: int | None
    keyword_rank: int | None
    vector_score: float | None
    keyword_score: float | None
    fusion_score: float
    fusion_rank: int
    gefunden_ueber: str  # "vector" | "keyword" | "beide"


def reciprocal_rank_fusion(
    vector_hits: list[VectorSearchHit], keyword_hits: list[KeywordSearchHit], *, k: int = _RRF_K
) -> list[FusedHit]:
    vector_by_id = {h.chunk_id: h for h in vector_hits}
    keyword_by_id = {h.chunk_id: h for h in keyword_hits}
    # Reihenfolge (erst Vektor-, dann Keyword-Treffer) ist hier nur fuer
    # deterministische Score-Gleichstaende relevant, nicht fuer die Fusion selbst.
    all_chunk_ids = list(
        dict.fromkeys([h.chunk_id for h in vector_hits] + [h.chunk_id for h in keyword_hits])
    )

    scored: list[tuple[str, float]] = []
    for chunk_id in all_chunk_ids:
        score = 0.0
        v = vector_by_id.get(chunk_id)
        kw = keyword_by_id.get(chunk_id)
        if v is not None:
            score += 1 / (k + v.vector_rank)
        if kw is not None:
            score += 1 / (k + kw.keyword_rank)
        scored.append((chunk_id, score))

    scored.sort(key=lambda item: item[1], reverse=True)

    fused: list[FusedHit] = []
    for rank, (chunk_id, score) in enumerate(scored, start=1):
        v = vector_by_id.get(chunk_id)
        kw = keyword_by_id.get(chunk_id)
        if v is not None and kw is not None:
            gefunden_ueber = "beide"
        elif v is not None:
            gefunden_ueber = "vector"
        else:
            gefunden_ueber = "keyword"
        fused.append(
            FusedHit(
                chunk_id=chunk_id,
                document_id=v.document_id if v is not None else kw.document_id,
                vector_rank=v.vector_rank if v is not None else None,
                keyword_rank=kw.keyword_rank if kw is not None else None,
                vector_score=v.vector_score if v is not None else None,
                keyword_score=kw.keyword_score if kw is not None else None,
                fusion_score=score,
                fusion_rank=rank,
                gefunden_ueber=gefunden_ueber,
            )
        )
    return fused
