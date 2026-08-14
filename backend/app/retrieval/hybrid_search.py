from sqlalchemy.orm import Session

from app.retrieval.fusion import FusedHit, reciprocal_rank_fusion
from app.retrieval.keyword_search import keyword_search
from app.retrieval.reranker import rerank
from app.retrieval.vector_search import vector_search
from app.services.settings_service import get_app_settings


def hybrid_search(db: Session, project_id: int, query: str, *, final_k_override: int | None = None) -> list[FusedHit]:
    """Orchestriert den vollstaendigen Hybrid-Retrieval-Ablauf (Briefing Punkt
    7): candidate_k je Suchpfad aus den RAG-Settings holen, Vektor- und
    Keyword-Suche parallel (hier sequenziell, da beide schnell sind und keine
    Nebenlaeufigkeit noetig ist) ausfuehren, per Reciprocal Rank Fusion
    kombinieren, durch die (aktuell Passthrough-)Rerank-Schnittstelle geben und
    auf final_k kappen.

    final_k_override erlaubt der Retrieval-Test-Ansicht (Schritt 4/10), final_k
    fuer eine einzelne Debug-Anfrage zu ueberschreiben, ohne die globalen
    RAG-Settings zu aendern; candidate_k_vector/candidate_k_keyword kommen
    davon unberuehrt immer aus den globalen Settings.
    """
    app_settings = get_app_settings(db)

    vector_hits = vector_search(db, project_id, query, app_settings.candidate_k_vector)
    keyword_hits = keyword_search(db, project_id, query, app_settings.candidate_k_keyword)

    fused = reciprocal_rank_fusion(vector_hits, keyword_hits)
    reranked = rerank(fused, query)

    final_k = final_k_override if final_k_override is not None else app_settings.final_k
    return reranked[:final_k]
