import logging


def setup_logging(level: int = logging.INFO) -> None:
    """Einfaches strukturiertes Logging.

    Datenschutz-Grundsatz (siehe Briefing, nicht-funktionale Anforderungen): an
    keiner Stelle im Code werden API-Keys, vollstaendige Dokument-/Chat-Texte oder
    das Encryption-Secret geloggt - Fehler bleiben ueber IDs (document_id,
    project_id, request_id) und Fehlertyp nachvollziehbar, nicht ueber Rohinhalte.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
