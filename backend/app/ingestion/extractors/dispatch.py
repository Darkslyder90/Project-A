from pathlib import Path

from app.ingestion.extractors import docx as docx_extractor
from app.ingestion.extractors import pdf as pdf_extractor
from app.ingestion.extractors import txt as txt_extractor
from app.ingestion.extractors.base import ExtractedContent

_EXTRACTORS = {
    ".pdf": pdf_extractor.extract,
    ".docx": docx_extractor.extract,
    ".txt": txt_extractor.extract,
    ".md": txt_extractor.extract,
}


def extract_text(path: Path, extension: str) -> ExtractedContent:
    extractor = _EXTRACTORS.get(extension)
    if extractor is None:
        raise ValueError(f"Kein Extractor fuer Dateiendung '{extension}' registriert.")
    return extractor(path)
