from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import re
from typing import Any, Iterable, Protocol

from .models import PatternCard


@dataclass(frozen=True)
class ResearchSource:
    source_id: str
    name: str
    source_type: str
    allowlisted: bool
    status: str
    refresh_policy: str
    license: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchDocument:
    document_id: str
    source_id: str
    version: str
    title: str
    body: str
    checksum: str
    published_at: str
    fetched_at: str
    source_status: str
    license: str
    citation_url: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalHit:
    document_id: str
    source_id: str
    title: str
    rank: int
    score: float
    snippet: str
    checksum: str
    published_at: str
    fetched_at: str
    source_status: str
    citation_url: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PostgresResearchSearchPlan:
    sql: str
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BUILTIN_RESEARCH_SOURCES: tuple[ResearchSource, ...] = (
    ResearchSource(
        source_id="sebi-publications",
        name="SEBI Publications",
        source_type="regulator",
        allowlisted=True,
        status="enabled",
        refresh_policy="daily",
        license="public_reference",
        notes=[
            "Admin-managed public regulator source; URL configuration stays outside MCP.",
            "Used for policy, circular, and market-structure research provenance.",
        ],
    ),
    ResearchSource(
        source_id="nse-announcements",
        name="NSE Announcements",
        source_type="exchange",
        allowlisted=True,
        status="enabled",
        refresh_policy="daily_plus_exchange_incremental",
        license="public_reference",
        notes=[
            "Admin-managed public exchange announcement source.",
            "Incremental refresh is scheduled by source identifier and normalized query.",
        ],
    ),
    ResearchSource(
        source_id="bse-announcements",
        name="BSE Announcements",
        source_type="exchange",
        allowlisted=True,
        status="enabled",
        refresh_policy="daily_plus_exchange_incremental",
        license="public_reference",
        notes=[
            "Admin-managed public exchange announcement source.",
            "The agent can request refresh by registered source identifier only.",
        ],
    ),
    ResearchSource(
        source_id="issuer-investor-relations",
        name="Registered Issuer Investor Relations",
        source_type="issuer_ir",
        allowlisted=True,
        status="enabled",
        refresh_policy="daily",
        license="issuer_public_reference",
        notes=[
            "Admin-managed issuer domains only; arbitrary user-supplied pages are excluded.",
            "Issuer domains must be registered before documents enter the research store.",
        ],
    ),
)


class ResearchStore(Protocol):
    def search(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        ...

    def get_document(self, document_id: str) -> ResearchDocument:
        ...


class PatternStore(Protocol):
    def search(
        self,
        query: str,
        *,
        tags: Iterable[str] | None = None,
        limit: int = 5,
    ) -> list[PatternCard]:
        ...

    def get(self, pattern_id: str) -> PatternCard:
        ...


class FileBackedResearchStore:
    def __init__(self, documents: Iterable[ResearchDocument]) -> None:
        self._documents = {document.document_id: document for document in documents}

    @classmethod
    def from_pattern_cards(
        cls,
        cards: Iterable[PatternCard],
        *,
        source_id: str = "pattern-store-fixture",
        fetched_at: str = "2026-07-27T00:00:00Z",
    ) -> FileBackedResearchStore:
        return cls(
            pattern_card_to_research_document(
                card,
                source_id=source_id,
                fetched_at=fetched_at,
            )
            for card in cards
        )

    def search(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        terms = _terms(query)
        scored: list[tuple[int, str, ResearchDocument]] = []
        for document in self._documents.values():
            haystack = " ".join(
                [
                    document.title,
                    document.body,
                    str(document.metadata.get("setup_type", "")),
                    " ".join(document.metadata.get("tags", [])),
                ]
            ).lower()
            score = sum(1 for term in terms if term in haystack)
            if not terms or score > 0:
                scored.append((score, document.document_id, document))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [
            RetrievalHit(
                document_id=document.document_id,
                source_id=document.source_id,
                title=document.title,
                rank=index,
                score=float(score),
                snippet=_snippet(document.body, terms),
                checksum=document.checksum,
                published_at=document.published_at,
                fetched_at=document.fetched_at,
                source_status=document.source_status,
                citation_url=document.citation_url,
                metadata=document.metadata,
            )
            for index, (score, _, document) in enumerate(scored[: max(0, limit)], start=1)
        ]

    def get_document(self, document_id: str) -> ResearchDocument:
        document = self._documents.get(document_id)
        if document is None:
            raise ValueError(f"Unknown research document: {document_id}")
        return document


class FileBackedPatternStore:
    def __init__(self, cards: Iterable[PatternCard]) -> None:
        self._cards = {card.pattern_id: card for card in cards}

    def search(
        self,
        query: str,
        *,
        tags: Iterable[str] | None = None,
        limit: int = 5,
    ) -> list[PatternCard]:
        terms = _terms(query)
        tag_filter = {tag.strip().lower() for tag in tags or [] if tag.strip()}

        def score(card: PatternCard) -> int:
            haystack = " ".join(
                [
                    card.pattern_id,
                    card.title,
                    card.setup_type,
                    card.summary,
                    " ".join(card.tags),
                    " ".join(card.evidence),
                ]
            ).lower()
            term_score = sum(1 for term in terms if term in haystack)
            tag_score = 2 if tag_filter and tag_filter.intersection(card.tags) else 0
            return term_score + tag_score

        cards = [
            card
            for card in self._cards.values()
            if not tag_filter or tag_filter.intersection(set(card.tags))
        ]
        cards.sort(key=lambda card: (score(card), card.pattern_id), reverse=True)
        if terms or tag_filter:
            cards = [card for card in cards if score(card) > 0]
        return cards[: max(0, limit)]

    def get(self, pattern_id: str) -> PatternCard:
        card = self._cards.get(pattern_id)
        if card is None:
            raise ValueError(f"Unknown pattern_id: {pattern_id}")
        return card

    def as_research_store(self) -> FileBackedResearchStore:
        return FileBackedResearchStore.from_pattern_cards(self._cards.values())


def normalize_research_query(query: str) -> str:
    normalized = " ".join(query.strip().split())
    lowered = normalized.lower()
    if (
        "://" in lowered
        or lowered.startswith("www.")
        or re.search(r"\b[a-z0-9.-]+\.(com|in|org|net|io|co)\b", lowered)
    ):
        raise ValueError(
            "Research query must target a registered research source, symbol, or normalized topic; arbitrary URLs are not accepted."
        )
    return normalized


def build_postgres_research_search_query(
    *,
    tenant_id: str,
    query: str,
    normalized_symbol: str | None = None,
    limit: int = 5,
) -> PostgresResearchSearchPlan:
    normalized_query = normalize_research_query(query)
    bounded_limit = max(1, min(int(limit), 20))
    return PostgresResearchSearchPlan(
        sql="""
        SELECT
            d.id,
            d.source_id,
            d.document_key,
            d.title,
            d.normalized_symbol,
            d.published_at,
            d.fetched_at,
            d.checksum,
            d.source_status,
            d.content,
            d.provenance,
            d.license_metadata,
            ts_rank_cd(d.search_vector, plainto_tsquery('english', %(query)s)) AS score
        FROM research_documents d
        JOIN research_sources s
            ON s.id = d.source_id
           AND s.tenant_id = d.tenant_id
        WHERE d.tenant_id = %(tenant_id)s
          AND s.status = 'enabled'
          AND d.source_status = 'available'
          AND d.search_vector @@ plainto_tsquery('english', %(query)s)
          AND (
              %(normalized_symbol)s IS NULL
              OR d.normalized_symbol IS NULL
              OR d.normalized_symbol = %(normalized_symbol)s
          )
        ORDER BY score DESC, d.published_at DESC NULLS LAST, d.fetched_at DESC, d.id
        LIMIT %(limit)s
        """.strip(),
        params={
            "tenant_id": tenant_id,
            "query": normalized_query,
            "normalized_symbol": normalized_symbol,
            "limit": bounded_limit,
        },
    )


def pattern_card_to_research_document(
    card: PatternCard,
    *,
    source_id: str,
    fetched_at: str,
) -> ResearchDocument:
    body = "\n".join(
        [
            card.summary,
            *card.prerequisites,
            *card.evidence,
            *card.counterevidence,
            *card.risk_notes,
        ]
    )
    citation_url = card.citations[0].url if card.citations else ""
    checksum = "sha256:" + sha256(body.encode("utf-8")).hexdigest()
    return ResearchDocument(
        document_id=f"pattern:{card.pattern_id}:{card.version}",
        source_id=source_id,
        version=card.version,
        title=card.title,
        body=body,
        checksum=checksum,
        published_at="2026-01-01T00:00:00Z",
        fetched_at=fetched_at,
        source_status="fresh",
        license="public_reference",
        citation_url=citation_url,
        metadata={
            "pattern_id": card.pattern_id,
            "setup_type": card.setup_type,
            "tags": card.tags,
            "source_type": card.source_type,
        },
    )


def _terms(query: str) -> list[str]:
    return [term for term in query.lower().split() if term]


def _snippet(body: str, terms: list[str]) -> str:
    if not terms:
        return body[:220]
    lowered = body.lower()
    first_match = min(
        (lowered.find(term) for term in terms if term in lowered),
        default=0,
    )
    start = max(0, first_match - 60)
    return body[start : start + 220]
