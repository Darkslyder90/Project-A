from app.retrieval.fusion import FusedHit


def rerank(hits: list[FusedHit], query: str) -> list[FusedHit]:  # noqa: ARG001
    """Passthrough-Implementierung (siehe Briefing: Architektur-Vorgabe fuer
    spaetere Erweiterung nach der Fusion). Definierte Schnittstelle
    (Kandidatenliste + Query rein -> ggf. neu sortierte Liste raus), damit sich
    spaeter ein lokaler Cross-Encoder (z. B. sentence-transformers CrossEncoder,
    offline) einklinken laesst, ohne hybrid_search() oder die Aufrufer
    umzubauen. Fuer den MVP unveraendert die Fusion-Reihenfolge.
    """
    return hits
