import re

from app.ingestion.chunkers.base import ChunkCandidate
from app.ingestion.chunkers.token_chunker import chunk_by_tokens
from app.ingestion.embedding.embedder import Embedder

# Erkennt Sprecherwechsel-Zeilen wie "Max Mustermann: ..." oder "MM: ..." -
# bewusst restriktiv (kurzer Name/kurzes Kuerzel am Zeilenanfang gefolgt von
# Doppelpunkt), um Fliesstext mit zufaelligen Doppelpunkten nicht faelschlich
# als Sprecherwechsel zu erkennen.
_SPEAKER_RE = re.compile(r"^([A-ZÄÖÜ][\w.\-\s]{1,40}):\s+(.*)$", re.MULTILINE)

_MIN_TURN_FRACTION = 0.2


def has_speaker_turns(text: str) -> bool:
    return len(_SPEAKER_RE.findall(text)) >= 3


def _split_into_turns(text: str) -> list[str]:
    matches = list(_SPEAKER_RE.finditer(text))
    if not matches:
        return [text]

    turns: list[str] = []
    preamble = text[: matches[0].start()].strip()
    if preamble:
        turns.append(preamble)

    for i, match in enumerate(matches):
        turn_start = match.start()
        turn_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        turns.append(text[turn_start:turn_end].strip())

    return turns


def chunk_by_meeting_turns(
    text: str, embedder: Embedder, ziel_tokens: int, overlap_tokens: int
) -> list[ChunkCandidate]:
    """Chunking entlang Sprecherwechseln (siehe Briefing Punkt 5) - vermeidet,
    einen Sprecherwechsel mitten im Satz abzuschneiden. Mehrere aufeinander-
    folgende kurze Redebeitraege werden zu einem Chunk zusammengefasst, sehr
    lange Redebeitraege zusaetzlich tokenbasiert unterteilt.
    """
    turns = _split_into_turns(text)
    min_tokens = int(ziel_tokens * _MIN_TURN_FRACTION)

    merged: list[str] = []
    for turn_text in turns:
        if merged and embedder.count_tokens(merged[-1]) < min_tokens:
            merged[-1] = f"{merged[-1]}\n{turn_text}"
        else:
            merged.append(turn_text)

    chunks: list[ChunkCandidate] = []
    for block in merged:
        if embedder.count_tokens(block) <= ziel_tokens:
            chunks.append(ChunkCandidate(text=block))
        else:
            for sub in chunk_by_tokens(block, embedder, ziel_tokens, overlap_tokens):
                chunks.append(ChunkCandidate(text=sub.text))
    return chunks
