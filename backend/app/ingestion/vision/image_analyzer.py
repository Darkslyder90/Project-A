import base64
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.chat.claude_client import call_claude
from app.db.models.enums import ApiUsagePurpose

_MEDIA_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

# Feste Zwei-Block-Antwortstruktur (siehe Briefing: ocr_text = reiner erkannter
# Text, ki_analyse_rohtext = interpretierende Beschreibung - getrennt gehalten
# fuer Nachvollziehbarkeit). Kein strukturiertes Output-Schema noetig, ein
# einfaches Tag-Format reicht fuer den MVP und bleibt fuer den Reviewer lesbar,
# falls das Parsing doch mal fehlschlaegt (siehe Fallback unten).
_SYSTEM_PROMPT = (
    "Du analysierst einen Screenshot oder ein Foto aus einem SAP-Beratungsprojekt "
    "(z. B. Customizing-Einstellung, Fehlermeldung, Tabelle, Notiz auf Papier). "
    "Antworte ausschliesslich in exakt diesem Format, ohne jeglichen Text davor "
    "oder danach:\n\n"
    "<ocr_text>\n"
    "Woertlich im Bild sichtbarer Text, so genau wie moeglich abgeschrieben. "
    "Falls kein lesbarer Text im Bild vorkommt, lasse diesen Block leer.\n"
    "</ocr_text>\n"
    "<analyse>\n"
    "Kurze, sachliche Beschreibung/Interpretation des Bildinhalts (z. B. welcher "
    "SAP-Customizing-Pfad, welche Einstellung, welcher Bildschirm oder Sachverhalt "
    "zu sehen ist). Nur was im Bild tatsaechlich erkennbar ist, keine Vermutungen "
    "ueber nicht sichtbare Informationen.\n"
    "</analyse>"
)

_TAG_PATTERN = re.compile(r"<ocr_text>(.*?)</ocr_text>\s*<analyse>(.*?)</analyse>", re.DOTALL)

_NO_RESULT_TEXT = (
    "Die KI-Analyse hat kein auswertbares Ergebnis geliefert. Bitte Inhalt manuell erfassen."
)


@dataclass
class ImageAnalysisResult:
    ocr_text: str | None
    ki_analyse_rohtext: str


def analyze_image(
    db: Session, *, project_id: int, image_bytes: bytes, extension: str
) -> ImageAnalysisResult:
    """Sendet ein Bild zur Vision-Analyse an Claude (siehe Briefing Datenschutz-
    Abschnitt: bei einer Bildanalyse wird das Bild bewusst und transparent fuer
    genau diese Analyse uebertragen). Ergebnis wird in ocr_text/ki_analyse_rohtext
    getrennt - beide bleiben unveraendert als Rohdaten erhalten, auch wenn der
    Nutzer die daraus abgeleitete `inhalt`-Fassung im Review-Schritt bearbeitet.
    """
    media_type = _MEDIA_TYPES.get(extension)
    if media_type is None:
        raise ValueError(f"Kein unterstuetzter Bildtyp fuer Vision-Analyse: '{extension}'.")

    encoded = base64.standard_b64encode(image_bytes).decode("utf-8")
    result = call_claude(
        db,
        project_id=project_id,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": encoded},
                    },
                    {"type": "text", "text": "Analysiere dieses Bild wie im System-Prompt beschrieben."},
                ],
            }
        ],
        zweck=ApiUsagePurpose.IMAGE_ANALYSIS,
        max_tokens=2048,
    )

    if result.stop_reason == "refusal" or not result.text.strip():
        return ImageAnalysisResult(ocr_text=None, ki_analyse_rohtext=_NO_RESULT_TEXT)

    match = _TAG_PATTERN.search(result.text)
    if not match:
        # Format nicht wie erwartet - trotzdem kein Blackbox-Fehler: die volle,
        # ungeparste Antwort landet in ki_analyse_rohtext und bleibt im
        # Review-Schritt sichtbar/editierbar statt den Task fehlschlagen zu lassen.
        return ImageAnalysisResult(ocr_text=None, ki_analyse_rohtext=result.text.strip())

    ocr_text = match.group(1).strip() or None
    ki_analyse_rohtext = match.group(2).strip()
    return ImageAnalysisResult(ocr_text=ocr_text, ki_analyse_rohtext=ki_analyse_rohtext)
