from app.chat.source_validator import extract_cited_source_ids, find_invalid_citations


def test_extract_cited_source_ids_finds_all_citations():
    text = "Laut [S1] ist das so. Auch [S2][S3] bestaetigen das."
    assert extract_cited_source_ids(text) == {"S1", "S2", "S3"}


def test_extract_cited_source_ids_returns_empty_set_without_citations():
    assert extract_cited_source_ids("Dazu finde ich keine Informationen.") == set()


def test_find_invalid_citations_flags_unknown_source_id():
    text = "Laut [S1] und [S5] ist das so."
    invalid = find_invalid_citations(text, valid_source_ids={"S1", "S2"})
    assert invalid == ["S5"]


def test_find_invalid_citations_empty_when_all_valid():
    text = "Laut [S1] und [S2] ist das so."
    invalid = find_invalid_citations(text, valid_source_ids={"S1", "S2", "S3"})
    assert invalid == []
