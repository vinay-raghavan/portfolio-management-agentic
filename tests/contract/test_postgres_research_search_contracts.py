from __future__ import annotations

from pathlib import Path

import pytest

from portfolio_domain import (
    BUILTIN_RESEARCH_SOURCES,
    PostgresResearchStore,
    build_postgres_research_search_query,
    normalize_research_query,
)
from portfolio_mcp.tools import EXPOSED_TOOL_NAMES, search_curated_research
from portfolio_policy import ActionTier, classify_tool


def test_builtin_research_sources_are_allowlisted_public_sources() -> None:
    source_ids = {source.source_id for source in BUILTIN_RESEARCH_SOURCES}

    assert {"sebi-publications", "nse-announcements", "bse-announcements"}.issubset(source_ids)
    for source in BUILTIN_RESEARCH_SOURCES:
        payload = source.to_dict()
        assert payload["allowlisted"] is True
        assert payload["status"] == "enabled"
        assert payload["source_type"] in {"regulator", "exchange", "issuer_ir"}
        assert "http://" not in str(payload).lower()
        assert "token" not in str(payload).lower()


def test_research_query_normalization_rejects_arbitrary_urls() -> None:
    assert normalize_research_query("  infy breakout   volume ") == "infy breakout volume"

    with pytest.raises(ValueError, match="empty"):
        normalize_research_query("   ")

    with pytest.raises(ValueError, match="registered research source"):
        normalize_research_query("https://example.com/research")


def test_postgres_research_search_query_is_tenant_scoped_allowlisted_and_full_text() -> None:
    plan = build_postgres_research_search_query(
        tenant_id="tenant-123",
        query="INFY volume breakout",
        normalized_symbol="NSE:INFY-EQ",
        limit=12,
    )

    sql = plan.sql.lower()
    assert "tenant_id = %(tenant_id)s" in sql
    assert "research_sources" in sql
    assert "research_documents" in sql
    assert "s.status = 'enabled'" in sql
    assert "d.source_status = 'available'" in sql
    assert "plainto_tsquery" in sql
    assert "ts_rank_cd" in sql
    assert "search_vector @@" in sql
    assert "embedding" not in sql
    assert "vector" not in sql.replace("search_vector", "")
    assert plan.params == {
        "tenant_id": "tenant-123",
        "query": "INFY volume breakout",
        "normalized_symbol": "NSE:INFY-EQ",
        "limit": 12,
    }


def test_research_search_vector_migration_maintains_full_text_without_pgvector() -> None:
    migration = Path(
        "infra/db/alembic/versions/20260727_0002_research_search_vector_trigger.py"
    ).read_text()

    assert "to_tsvector('english'" in migration
    assert "research_documents_search_vector_refresh" in migration
    assert "BEFORE INSERT OR UPDATE" in migration
    assert "ix_research_documents_tenant_status_published" in migration
    assert "pgvector" not in migration.lower()
    assert "embedding" not in migration.lower()


def test_search_curated_research_mcp_tool_is_read_only_and_fixture_backed() -> None:
    assert "search_curated_research" in EXPOSED_TOOL_NAMES
    assert classify_tool("search_curated_research") == ActionTier.READ_ONLY

    result = search_curated_research("volatility sizing", limit=2)

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert result["retrieval"]["mode"] == "file_backed_fixture"
    assert result["retrieval"]["backend"] == "lexical"
    assert result["retrieval"]["vector_retrieval"] == "disabled"
    assert result["hits"]
    assert result["hits"][0]["source_status"] == "fresh"
    assert result["hits"][0]["checksum"].startswith("sha256:")
    assert "embedding" not in str(result).lower()


class _FakeCursor:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.executed: list[tuple[str, dict]] = []
        self.description = [(key,) for key in rows[0]] if rows else []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, sql: str, params: dict) -> None:
        self.executed.append((sql, params))

    def fetchall(self) -> list[dict]:
        return self.rows

    def fetchone(self) -> dict | None:
        return self.rows[0] if self.rows else None


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self.cursor_instance = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self.cursor_instance


def test_postgres_research_store_executes_tenant_scoped_full_text_search() -> None:
    cursor = _FakeCursor(
        [
            {
                "id": "doc-1",
                "source_id": "source-1",
                "document_key": "nse:infy:announcement",
                "title": "INFY volume breakout filing",
                "normalized_symbol": "NSE:INFY-EQ",
                "published_at": "2026-07-26T10:00:00Z",
                "fetched_at": "2026-07-26T10:15:00Z",
                "checksum": "sha256:abc",
                "source_status": "available",
                "content": "INFY reported volume breakout context with risk notes.",
                "provenance": {
                    "citation_url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
                    "source_path": "/tmp/local-should-not-leak.json",
                },
                "license_metadata": {"usage": "public_reference"},
                "score": 0.92,
            }
        ]
    )
    store = PostgresResearchStore(
        tenant_id="tenant-123",
        connection_factory=lambda: _FakeConnection(cursor),
    )

    hits = store.search(
        "INFY volume breakout",
        normalized_symbol="NSE:INFY-EQ",
        limit=3,
    )

    assert len(hits) == 1
    hit = hits[0]
    assert hit.document_id == "doc-1"
    assert hit.rank == 1
    assert hit.score == 0.92
    assert hit.source_status == "available"
    assert hit.citation_url.startswith("https://www.nseindia.com/")
    assert hit.metadata["document_key"] == "nse:infy:announcement"
    assert hit.metadata["license_metadata"] == {"usage": "public_reference"}
    assert "source_path" not in str(hit.to_dict())
    assert "embedding" not in str(hit.to_dict()).lower()
    sql, params = cursor.executed[0]
    assert "tenant_id = %(tenant_id)s" in sql
    assert "plainto_tsquery" in sql
    assert params == {
        "tenant_id": "tenant-123",
        "query": "INFY volume breakout",
        "normalized_symbol": "NSE:INFY-EQ",
        "limit": 3,
    }


def test_postgres_research_store_get_document_is_tenant_scoped() -> None:
    cursor = _FakeCursor(
        [
            {
                "id": "doc-1",
                "source_id": "source-1",
                "document_key": "sebi:circular",
                "title": "SEBI circular",
                "published_at": "2026-07-25T09:00:00Z",
                "fetched_at": "2026-07-25T09:10:00Z",
                "checksum": "sha256:def",
                "source_status": "available",
                "content": "SEBI circular body",
                "provenance": {"citation_url": "https://www.sebi.gov.in/"},
                "license_metadata": {"usage": "public_reference"},
            }
        ]
    )
    store = PostgresResearchStore(
        tenant_id="tenant-123",
        connection_factory=lambda: _FakeConnection(cursor),
    )

    document = store.get_document("doc-1")

    assert document.document_id == "doc-1"
    assert document.version == "sebi:circular"
    assert document.body == "SEBI circular body"
    assert document.citation_url == "https://www.sebi.gov.in/"
    sql, params = cursor.executed[0]
    assert "WHERE d.tenant_id = %(tenant_id)s" in sql
    assert "AND d.id = %(document_id)s" in sql
    assert params == {"tenant_id": "tenant-123", "document_id": "doc-1"}


def test_postgres_research_store_rejects_invalid_queries_without_executing() -> None:
    cursor = _FakeCursor([])
    store = PostgresResearchStore(
        tenant_id="tenant-123",
        connection_factory=lambda: _FakeConnection(cursor),
    )

    with pytest.raises(ValueError, match="arbitrary URLs"):
        store.search("https://example.com/not-allowlisted")

    assert cursor.executed == []
