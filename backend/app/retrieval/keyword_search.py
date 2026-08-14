import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.indexing.index_metadata_service import get_index_metadata

_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


@dataclass
class KeywordSearchHit:
    chunk_id: str
    document_id: int
    keyword_rank: int
    keyword_score: float  # bm25(): kleiner = relevanter (SQLite-Konvention)


def _build_match_query(query_text: str) -> str | None:
    """Baut eine gegen FTS5-Syntaxfehler robuste MATCH-Abfrage: jedes Token wird
    als eigenes, in Anfuehrungszeichen gesetztes Phrase-Literal behandelt statt
    rohen Nutzertext direkt in MATCH zu interpolieren (schuetzt vor
    FTS5-Sonderzeichen wie "-", ":", '"' und reservierten Operatoren wie
    AND/OR/NOT/NEAR im Suchtext). Tokens werden mit OR verknuepft, damit auch
    Teiltreffer gefunden werden - Ziel laut Briefing: exakte Treffer fuer
    Transaktionscodes (VA02), Tabellen (VBAP), Ticketnummern, Eigennamen
    zuverlaessig finden, auch wenn Embeddings dort schwaecheln.
    """
    tokens = _TOKEN_PATTERN.findall(query_text)
    if not tokens:
        return None
    quoted = [f'"{t.replace(chr(34), chr(34) * 2)}"' for t in tokens]
    return " OR ".join(quoted)


def keyword_search(db: Session, project_id: int, query_text: str, top_k: int) -> list[KeywordSearchHit]:
    """Keyword-/Volltextsuchpfad des Hybrid Retrieval (SQLite FTS5, siehe
    Briefing Punkt 7). Zwingend gefiltert auf project_id UND die aktuell aktive
    index_version (siehe Briefing: Projektisolation im Retrieval) - dieselbe
    Isolationslogik wie beim Vektorsuchpfad (vector_search.py), nur eben fuer
    den FTS-Zweig: waehrend eines spaeteren Rebuilds duerfen Chunks der
    pending_index_version bereits im FTS-Index stehen, aber nicht ins
    Retrieval einfliessen.
    """
    index_meta = get_index_metadata(db, project_id)
    if index_meta.active_index_version == 0:
        return []

    match_query = _build_match_query(query_text)
    if match_query is None:
        return []

    sql = text(
        """
        SELECT c.id AS chunk_id, c.document_id AS document_id, bm25(chunk_fts) AS score
        FROM chunk_fts
        JOIN chunks c ON c.rowid = chunk_fts.rowid
        JOIN documents d ON d.id = c.document_id
        WHERE chunk_fts MATCH :match_query
          AND d.project_id = :project_id
          AND d.deleted_at IS NULL
          AND c.index_version = :index_version
        ORDER BY score
        LIMIT :limit
        """
    )
    rows = db.execute(
        sql,
        {
            "match_query": match_query,
            "project_id": project_id,
            "index_version": index_meta.active_index_version,
            "limit": top_k,
        },
    ).all()

    return [
        KeywordSearchHit(
            chunk_id=row.chunk_id, document_id=row.document_id, keyword_rank=rank, keyword_score=row.score
        )
        for rank, row in enumerate(rows, start=1)
    ]
