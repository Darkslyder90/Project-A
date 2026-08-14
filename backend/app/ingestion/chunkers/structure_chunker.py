import re

from app.ingestion.chunkers.base import ChunkCandidate
from app.ingestion.chunkers.token_chunker import chunk_by_tokens
from app.ingestion.embedding.embedder import Embedder

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$", re.MULTILINE)

# Abschnitte, die kleiner als dieser Bruchteil des Zieltokenwerts sind, werden
# mit dem naechsten Abschnitt zusammengefasst statt einen eigenen Mini-Chunk zu
# bilden (siehe Briefing: "sehr kurze thematisch zusammengehoerige Abschnitte
# duerfen zusammengefasst werden").
_MIN_SECTION_FRACTION = 0.2


def has_markdown_structure(text: str) -> bool:
    return len(_HEADING_RE.findall(text)) >= 2


def _split_into_sections(text: str) -> list[tuple[str | None, str]]:
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [(None, text)]

    sections: list[tuple[str | None, str]] = []
    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append((None, preamble))

    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        sections.append((heading, f"{heading}\n{body}" if body else heading))

    return sections


def chunk_by_structure(
    text: str, embedder: Embedder, ziel_tokens: int, overlap_tokens: int
) -> list[ChunkCandidate]:
    """Struktur-/abschnittsbasiertes Chunking entlang Markdown-Ueberschriften
    (siehe Briefing Punkt 5).
    """
    sections = _split_into_sections(text)

    min_tokens = int(ziel_tokens * _MIN_SECTION_FRACTION)
    merged: list[tuple[str | None, str]] = []
    for heading, body in sections:
        if merged and embedder.count_tokens(merged[-1][1]) < min_tokens:
            prev_heading, prev_body = merged[-1]
            merged[-1] = (prev_heading, f"{prev_body}\n\n{body}")
        else:
            merged.append((heading, body))

    chunks: list[ChunkCandidate] = []
    for heading, body in merged:
        if embedder.count_tokens(body) <= ziel_tokens:
            chunks.append(ChunkCandidate(text=body, abschnitt=heading))
        else:
            # Zu langer Abschnitt: zusaetzlich tokenbasiert mit Overlap unterteilen.
            for sub in chunk_by_tokens(body, embedder, ziel_tokens, overlap_tokens):
                chunks.append(ChunkCandidate(text=sub.text, abschnitt=heading))
    return chunks
