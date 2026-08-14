from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.chat.claude_client import call_claude
from app.chat.prompt_builder import PromptSource, build_system_prompt
from app.chat.source_validator import extract_cited_source_ids, find_invalid_citations
from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.db.models.enums import ApiUsagePurpose
from app.retrieval.vector_search import vector_search
from app.services.project_service import get_project
from app.services.settings_service import get_app_settings

_UNZUREICHEND = "Dazu finde ich in den Projektdaten keine ausreichenden Informationen."


@dataclass
class ChatAnswer:
    antwort: str
    quellen: list[PromptSource]
    unbekannte_zitate: list[str]


def _build_sources(db: Session, project_id: int, query: str, top_k: int) -> list[PromptSource]:
    # Schritt 5: reine Vektorsuche (Hybrid Retrieval mit FTS5 kommt Schritt 10) -
    # final_k wird hier direkt als top_k der Vektorsuche verwendet, da es noch
    # keine Fusion mehrerer Suchpfade gibt.
    hits = vector_search(db, project_id, query, top_k)
    if not hits:
        return []

    chunk_ids = [h.chunk_id for h in hits]
    chunks_by_id = {c.id: c for c in db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()}

    document_ids = {h.document_id for h in hits}
    titles_by_document_id = {
        d.id: d.titel for d in db.query(Document).filter(Document.id.in_(document_ids)).all()
    }

    sources: list[PromptSource] = []
    for i, hit in enumerate(hits):
        chunk = chunks_by_id.get(hit.chunk_id)
        if chunk is None:
            continue
        sources.append(
            PromptSource(
                source_id=f"S{i + 1}",
                chunk_id=chunk.id,
                document_id=hit.document_id,
                document_titel=titles_by_document_id.get(hit.document_id, "(unbekannt)"),
                dokumentdatum=chunk.dokumentdatum,
                abschnitt=chunk.abschnitt,
                text=chunk.text,
            )
        )
    return sources


def ask(db: Session, project_id: int, query: str) -> ChatAnswer:
    get_project(db, project_id)  # 404, falls Projekt nicht existiert

    app_settings = get_app_settings(db)
    sources = _build_sources(db, project_id, query, app_settings.final_k)

    system_prompt = build_system_prompt(sources)
    result = call_claude(
        db,
        project_id=project_id,
        system=system_prompt,
        messages=[{"role": "user", "content": query}],
        zweck=ApiUsagePurpose.CHAT,
    )

    if result.stop_reason == "refusal":
        return ChatAnswer(
            antwort="Claude konnte diese Anfrage leider nicht beantworten.",
            quellen=[],
            unbekannte_zitate=[],
        )

    valid_ids = {s.source_id for s in sources}
    invalid = find_invalid_citations(result.text, valid_ids)
    cited_ids = extract_cited_source_ids(result.text) & valid_ids
    used_sources = [s for s in sources if s.source_id in cited_ids]

    return ChatAnswer(antwort=result.text, quellen=used_sources, unbekannte_zitate=invalid)
