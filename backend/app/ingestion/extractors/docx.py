from pathlib import Path

import docx as python_docx

from app.ingestion.extractors.base import ExtractedContent

# Word-Ueberschriften-Formatvorlagen -> Markdown-Ueberschriftenebene, damit der
# bestehende Struktur-Chunker (Schritt 3, erkennt '#'/'##'/'###') DOCX-Struktur
# transparent mitnutzen kann, ohne einen eigenen DOCX-Chunker zu brauchen.
_HEADING_STYLE_LEVELS: dict[str, int] = {
    "Heading 1": 1,
    "Heading 2": 2,
    "Heading 3": 3,
    "Titel": 1,  # deutsche Word-Sprachpakete
    "Ueberschrift 1": 1,
    "Ueberschrift 2": 2,
    "Ueberschrift 3": 3,
}


def extract(path: Path) -> ExtractedContent:
    document = python_docx.Document(str(path))

    lines: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        level = _HEADING_STYLE_LEVELS.get(paragraph.style.name if paragraph.style else "")
        if level:
            lines.append(f"{'#' * level} {text}")
        else:
            lines.append(text)

    dokumentdatum = None
    created = document.core_properties.created
    if created is not None:
        dokumentdatum = created.date()

    return ExtractedContent(text="\n\n".join(lines), dokumentdatum=dokumentdatum)
