import pytest

from app.db.models.enums import DocumentType
from app.ingestion.chunkers.dispatch import chunk_document
from app.ingestion.chunkers.meeting_chunker import chunk_by_meeting_turns, has_speaker_turns
from app.ingestion.chunkers.structure_chunker import chunk_by_structure, has_markdown_structure
from app.ingestion.chunkers.token_chunker import chunk_by_tokens
from app.ingestion.embedding.embedder import get_embedder


@pytest.fixture
def embedder(test_settings):
    return get_embedder("intfloat/multilingual-e5-base")


def test_token_chunker_respects_hard_model_limit(embedder):
    long_text = " ".join(f"Wort{i}" for i in range(2000))
    chunks = chunk_by_tokens(long_text, embedder, ziel_tokens=350, overlap_tokens=60)

    assert len(chunks) > 1
    for chunk in chunks:
        assert embedder.count_tokens(chunk.text) <= embedder.max_seq_length


def test_token_chunker_produces_overlap(embedder):
    long_text = " ".join(f"Wort{i}" for i in range(400))
    chunks = chunk_by_tokens(long_text, embedder, ziel_tokens=100, overlap_tokens=20)

    assert len(chunks) >= 2
    # Ende von Chunk 1 sollte sich mit dem Anfang von Chunk 2 ueberschneiden.
    words_chunk_1 = chunks[0].text.split()
    words_chunk_2 = chunks[1].text.split()
    assert any(w in words_chunk_2[:10] for w in words_chunk_1[-10:])


def test_structure_chunker_splits_on_headings(embedder):
    text = (
        "# Abschnitt A\n"
        + ("Text A. " * 50)
        + "\n# Abschnitt B\n"
        + ("Text B. " * 50)
    )
    assert has_markdown_structure(text)

    chunks = chunk_by_structure(text, embedder, ziel_tokens=350, overlap_tokens=60)

    assert len(chunks) >= 2
    assert any(c.abschnitt == "Abschnitt A" for c in chunks)
    assert any(c.abschnitt == "Abschnitt B" for c in chunks)


def test_structure_chunker_merges_short_sections(embedder):
    text = "# A\nkurz\n# B\nauch kurz\n# C\nnoch kuerzer"
    chunks = chunk_by_structure(text, embedder, ziel_tokens=350, overlap_tokens=60)

    # Drei sehr kurze Abschnitte sollten zu einem einzigen Chunk zusammengefasst werden.
    assert len(chunks) == 1


def test_meeting_chunker_splits_on_speaker_turns(embedder):
    turn_a = "Max Mustermann: " + "Wir sollten ueber das Berechtigungskonzept sprechen. " * 20
    turn_b = "Erika Musterfrau: " + "Ja, das steht noch aus. " * 20
    text = "\n".join([turn_a, turn_b, turn_a, turn_b])
    assert has_speaker_turns(text)

    chunks = chunk_by_meeting_turns(text, embedder, ziel_tokens=350, overlap_tokens=60)
    assert len(chunks) >= 1


def test_dispatch_uses_meeting_chunker_for_meeting_type_with_speakers(embedder):
    text = "\n".join(
        [
            "Max Mustermann: Punkt eins.",
            "Erika Musterfrau: Punkt zwei.",
            "Max Mustermann: Punkt drei.",
        ]
    )
    chunks = chunk_document(text, DocumentType.MEETING, embedder, ziel_tokens=350, overlap_tokens=60)
    assert len(chunks) >= 1


def test_dispatch_falls_back_to_token_chunker_for_plain_text(embedder):
    text = "Ein ganz normaler Fliesstext ohne Ueberschriften oder Sprecherwechsel."
    chunks = chunk_document(text, DocumentType.NOTIZ, embedder, ziel_tokens=350, overlap_tokens=60)
    assert len(chunks) == 1


def test_dispatch_returns_empty_for_blank_text(embedder):
    assert chunk_document("   ", DocumentType.NOTIZ, embedder, ziel_tokens=350, overlap_tokens=60) == []
