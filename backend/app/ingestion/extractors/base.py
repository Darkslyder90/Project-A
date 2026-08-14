from dataclasses import dataclass
from datetime import date


@dataclass
class ExtractedContent:
    text: str
    # Best-effort aus Dateimetadaten ermitteltes fachliches Datum (siehe
    # Briefing: "nach Moeglichkeit aus dem Dokument/Dateimetadaten uebernehmen,
    # sonst Upload-Zeitpunkt als Vorbelegung"). None, wenn nicht ermittelbar -
    # der Aufrufer entscheidet dann ueber den Fallback.
    dokumentdatum: date | None
