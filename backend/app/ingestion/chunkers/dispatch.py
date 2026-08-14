from app.db.models.enums import DocumentType
from app.ingestion.chunkers.base import ChunkCandidate
from app.ingestion.chunkers.meeting_chunker import chunk_by_meeting_turns, has_speaker_turns
from app.ingestion.chunkers.structure_chunker import chunk_by_structure, has_markdown_structure
from app.ingestion.chunkers.token_chunker import chunk_by_tokens
from app.ingestion.embedding.embedder import Embedder


def chunk_document(
    text: str, typ: DocumentType, embedder: Embedder, ziel_tokens: int, overlap_tokens: int
) -> list[ChunkCandidate]:
    """Waehlt die Chunking-Strategie je nach Dokumenttyp/erkennbarer Struktur
    (siehe Briefing Punkt 5): Meeting-Transkripte primaer an Sprecherwechseln,
    andere Typen primaer an Markdown-Ueberschriften, sonst tokenbasierter
    Fallback.
    """
    if not text or not text.strip():
        return []

    if typ == DocumentType.MEETING and has_speaker_turns(text):
        return chunk_by_meeting_turns(text, embedder, ziel_tokens, overlap_tokens)

    if has_markdown_structure(text):
        return chunk_by_structure(text, embedder, ziel_tokens, overlap_tokens)

    return chunk_by_tokens(text, embedder, ziel_tokens, overlap_tokens)
