from pathlib import Path

from pypdf import PdfReader

from app.ingestion.extractors.base import ExtractedContent


def extract(path: Path) -> ExtractedContent:
    """PDF: Text seitenweise extrahieren (Seitengrenzen als doppelte Zeilenumbrueche,
    damit der tokenbasierte Fallback-Chunker (Schritt 3) an sinnvollen Stellen
    trennen kann - PDFs haben i. d. R. keine fuer den Struktur-Chunker nutzbare
    Markdown-Gliederung). dokumentdatum best-effort aus /CreationDate.
    """
    reader = PdfReader(str(path))

    pages_text = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages_text)

    dokumentdatum = None
    if reader.metadata is not None and reader.metadata.creation_date is not None:
        dokumentdatum = reader.metadata.creation_date.date()

    return ExtractedContent(text=text, dokumentdatum=dokumentdatum)
