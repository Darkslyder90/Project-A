from pathlib import Path

from app.core.exceptions import ValidationAppError

# Erlaubte Formate fuer Schritt 7 (Textdokumente). Bilder kommen erst Schritt 9.
_ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


def validate_extension(original_filename: str) -> str:
    """Prueft die Dateiendung gegen die Allowlist und gibt sie normalisiert
    (lowercase, mit Punkt) zurueck. Der Original-Dateiname wird NIE fuer
    Dateisystempfade verwendet (siehe build_storage_relative_path) - hier nur
    zur Formatpruefung.
    """
    suffix = Path(original_filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(_ALLOWED_EXTENSIONS))
        raise ValidationAppError(
            f"Dateiformat '{suffix or '(keins)'}' wird nicht unterstuetzt. Erlaubt: {allowed}."
        )
    return suffix


def media_type_for_extension(extension: str) -> str:
    return _ALLOWED_EXTENSIONS.get(extension, "application/octet-stream")


def looks_like_plausible_content(extension: str, content: bytes) -> bool:
    """Einfache Magic-Byte-Pruefung als Plausibilisierung (siehe Briefing:
    "MIME-Type und Dateiendung plausibilisieren") - bewusst ohne Abhaengigkeit
    von libmagic/python-magic (zusaetzliche Systemabhaengigkeit, gerade fuer
    Windows-Dev-Umgebungen unnoetig kompliziert). PDF/DOCX haben verlaessliche
    Datei-Signaturen; TXT/MD werden stattdessen auf gueltiges UTF-8 geprueft.
    """
    if extension == ".pdf":
        return content[:5] == b"%PDF-"
    if extension == ".docx":
        return content[:4] == b"PK\x03\x04"  # DOCX ist ein ZIP-Container
    if extension in (".txt", ".md"):
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True
    return False


def build_storage_relative_path(project_id: int, document_id: int, extension: str) -> str:
    """Erzeugt einen sicheren, intern generierten relativen Pfad (siehe
    Briefing: Dateinamen niemals ungeprueft als Dateisystempfad verwenden).
    project_id/document_id sind Integer aus der DB, extension kommt aus der
    Allowlist oben - Pfad-Traversal ist damit strukturell ausgeschlossen,
    unabhaengig vom vom Nutzer hochgeladenen Original-Dateinamen.
    """
    return f"{project_id}/{document_id}/original{extension}"
