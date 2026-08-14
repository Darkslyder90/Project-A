from dataclasses import dataclass


@dataclass
class ChunkCandidate:
    text: str
    abschnitt: str | None = None
