from __future__ import annotations

from portfolio_domain import (
    FileBackedPatternStore,
    FileBackedResearchStore,
    PATTERN_CARDS,
    pattern_card_to_research_document,
    search_pattern_cards,
)


def test_pattern_cards_seed_file_backed_pattern_store() -> None:
    store = FileBackedPatternStore(PATTERN_CARDS)

    results = store.search("breakout volume", limit=3)
    first = store.get(results[0].pattern_id)

    assert len(PATTERN_CARDS) == 4
    assert results
    assert first.pattern_id == "breakout-continuation-v1"
    assert first.version == "1.0"
    assert first.citations
    assert first.source_type == "public_reference"


def test_pattern_store_matches_existing_pattern_search_contract() -> None:
    store = FileBackedPatternStore(PATTERN_CARDS)

    assert [card.pattern_id for card in store.search("momentum", tags=["technical"])] == [
        card.pattern_id
        for card in search_pattern_cards("momentum", tags=["technical"])
    ]


def test_pattern_cards_convert_to_research_documents_with_provenance() -> None:
    card = FileBackedPatternStore(PATTERN_CARDS).get("breakout-continuation-v1")

    document = pattern_card_to_research_document(
        card,
        source_id="pattern-store-fixture",
        fetched_at="2026-07-27T00:00:00Z",
    )

    assert document.document_id == "pattern:breakout-continuation-v1:1.0"
    assert document.source_id == "pattern-store-fixture"
    assert document.checksum.startswith("sha256:")
    assert document.source_status == "fresh"
    assert document.metadata["pattern_id"] == card.pattern_id
    assert document.metadata["tags"] == card.tags
    assert "Volume confirms demand" in document.body


def test_file_backed_research_store_returns_ranked_hits_without_embeddings() -> None:
    store = FileBackedResearchStore.from_pattern_cards(PATTERN_CARDS)

    hits = store.search("volatility sizing", limit=2)

    assert hits
    assert hits[0].rank == 1
    assert hits[0].score > 0
    assert hits[0].checksum.startswith("sha256:")
    assert hits[0].source_status == "fresh"
    assert hits[0].metadata["pattern_id"] == "volatility-regime-sizing-v1"
    assert "embedding" not in str([hit.to_dict() for hit in hits]).lower()
