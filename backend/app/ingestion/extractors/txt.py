from pathlib import Path

from app.ingestion.extractors.base import ExtractedContent


def extract(path: Path) -> ExtractedContent:
    """TXT/MD: keine verlaesslichen eingebetteten Metadaten - dokumentdatum
    bleibt None, der Aufrufer faellt auf den Upload-Zeitpunkt zurueck. Markdown
    braucht keine Sonderbehandlung: vorhandene '#'-Ueberschriften werden vom
    bestehenden Struktur-Chunker (Schritt 3) ohnehin erkannt.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    return ExtractedContent(text=text, dokumentdatum=None)
