from __future__ import annotations

from pathlib import Path

import pytest

from portfolio_domain import (
    BUILTIN_RESEARCH_SOURCES,
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
