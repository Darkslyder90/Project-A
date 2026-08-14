from app.ingestion.chunkers.base import ChunkCandidate
from app.ingestion.embedding.embedder import Embedder

# Puffer fuer das E5-Praefix ("passage: "/"query: ") und Spezial-Tokens
# (CLS/SEP), die beim tatsaechlichen Embedding zusaetzlich zum reinen Chunk-Text
# anfallen - siehe Embedder.embed_passages.
_TOKEN_SAFETY_MARGIN = 12


def chunk_by_tokens(
    text: str, embedder: Embedder, ziel_tokens: int, overlap_tokens: int
) -> list[ChunkCandidate]:
    """Tokenbasiertes Fallback-Chunking mit Overlap (siehe Briefing Punkt 5).

    Arbeitet direkt auf Token-IDs des Embedding-Modells (nicht auf Woertern),
    damit die harte Modellgrenze (max_seq_length) garantiert eingehalten wird -
    kein Chunk kann beim Embedding unbemerkt abgeschnitten werden.
    """
    ids = embedder.encode_ids(text)
    if not ids:
        return []

    max_tokens = max(1, min(ziel_tokens, embedder.max_seq_length - _TOKEN_SAFETY_MARGIN))
    overlap = max(0, min(overlap_tokens, max_tokens - 1))
    step = max_tokens - overlap

    chunks: list[ChunkCandidate] = []
    start = 0
    while start < len(ids):
        window = ids[start : start + max_tokens]
        decoded = embedder.decode_ids(window)
        if decoded:
            chunks.append(ChunkCandidate(text=decoded))
        if start + max_tokens >= len(ids):
            break
        start += step
    return chunks
