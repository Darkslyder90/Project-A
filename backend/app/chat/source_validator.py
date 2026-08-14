import re

_SOURCE_ID_RE = re.compile(r"\[S(\d+)\]")


def extract_cited_source_ids(text: str) -> set[str]:
    return {f"S{m}" for m in _SOURCE_ID_RE.findall(text)}


def find_invalid_citations(text: str, valid_source_ids: set[str]) -> list[str]:
    """Liefert Source-IDs, die Claude im Antworttext zitiert hat, die aber
    NICHT im tatsaechlich bereitgestellten Kontext existierten (siehe Briefing:
    Claude darf keine Metadaten/IDs erfinden). Sollte im Normalfall leer sein -
    der Aufrufer loggt/verwirft ungueltige Zitate, statt sie dem Nutzer als
    echte Quelle zu praesentieren.
    """
    cited = extract_cited_source_ids(text)
    return sorted(cited - valid_source_ids)
