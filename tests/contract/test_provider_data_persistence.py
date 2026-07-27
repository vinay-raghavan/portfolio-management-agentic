from __future__ import annotations

import sqlite3
from pathlib import Path

from portfolio_domain.models import FundamentalsSnapshot, UniverseMembers
from portfolio_domain.provider_data_store import (
    PostgresProviderDataStore,
    SQLiteProviderDataStore,
    build_provider_data_store,
)


TENANT_ID = "11111111-1111-1111-1111-111111111111"


class _FakeCursor:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.executed: list[tuple[str, dict]] = []
        self._rows = rows or []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, sql: str, params: dict) -> None:
        self.executed.append((sql, params))

    def fetchone(self):
        if not self._rows:
            return None
        return self._rows.pop(0)


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self.cursor_instance = cursor
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True


def _universe() -> UniverseMembers:
    return UniverseMembers(
        provider_id="configured_universe",
        universe_id="configured_growth",
        source="configured_json_file",
        as_of="2026-06-22",
        symbols=["DEMODATA", "SLOWDATA"],
        notes=["sanitized configured universe"],
    )


def _fundamentals() -> FundamentalsSnapshot:
    return FundamentalsSnapshot(
        provider_id="configured_fundamentals",
        source="configured_json_file",
        symbol="DEMODATA",
        as_of="2026-06-22",
        metrics={"quality_score": 0.82, "growth_score": 0.74},
        notes=["sanitized configured fundamentals"],
    )


def test_sqlite_provider_data_store_schema_is_separate_from_paper_ledger(tmp_path) -> None:
    db_path = tmp_path / "market-data.db"
    SQLiteProviderDataStore(db_path)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

    assert {
        "provider_universe_members",
        "provider_factor_snapshots",
    }.issubset(table_names)
    assert "paper_orders" not in table_names


def test_migration_adds_tenant_scoped_provider_context_tables() -> None:
    migration = Path(
        "infra/db/alembic/versions/20260727_0008_provider_context_store.py"
    ).read_text()

    assert 'revision = "20260727_0008"' in migration
    assert 'down_revision = "20260727_0007"' in migration
    assert "provider_universe_members" in migration
    assert "provider_factor_snapshots" in migration
    assert "tenant_id" in migration
    assert "payload" in migration
    assert "jsonb" in migration.lower()
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "tenant_isolation_{table_name}" in migration
    assert "DROP POLICY IF EXISTS" in migration
    assert "access_token" not in migration
    assert "credential" not in migration


def test_postgres_provider_data_store_records_tenant_scoped_universe_without_paths() -> None:
    universe = _universe()
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = PostgresProviderDataStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
    )

    stored = store.record_universe_members(universe)

    tenant_sql, tenant_params = cursor.executed[0]
    sql, params = cursor.executed[1]
    serialized = f"{sql} {params}".lower()
    assert "set_config('app.tenant_id'" in tenant_sql
    assert tenant_params == {"tenant_id": TENANT_ID}
    assert "INSERT INTO provider_universe_members" in sql
    assert "ON CONFLICT (tenant_id, provider_id, universe_id, as_of)" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["provider_id"] == "configured_universe"
    assert params["universe_id"] == "configured_growth"
    assert params["payload"] == universe.to_dict()
    assert stored.to_dict() == universe.to_dict()
    assert connection.committed is True
    assert "market-data.db" not in serialized
    assert "access_token" not in serialized
    assert "secret" not in serialized


def test_postgres_provider_data_store_records_and_reads_factor_snapshots() -> None:
    universe = _universe()
    fundamentals = _fundamentals()
    cursor = _FakeCursor(
        rows=[
            {"payload": universe.to_dict()},
            {"payload": fundamentals.to_dict()},
            {"row_count": 3},
            {"row_count": 4},
        ]
    )
    connection = _FakeConnection(cursor)
    store = PostgresProviderDataStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
    )

    stored_factor = store.record_fundamentals_snapshot(fundamentals)
    loaded_universe = store.get_universe_members("configured_growth")
    loaded_factor = store.get_fundamentals_snapshot("DEMODATA")
    universe_count = store.count_universe_members("configured_universe")
    factor_count = store.count_factor_snapshots("fundamentals", "configured_fundamentals")

    tenant_sql, tenant_params = cursor.executed[0]
    insert_sql, insert_params = cursor.executed[1]
    universe_sql, universe_params = cursor.executed[3]
    factor_sql, factor_params = cursor.executed[5]
    universe_count_sql, universe_count_params = cursor.executed[7]
    factor_count_sql, factor_count_params = cursor.executed[9]
    assert "set_config('app.tenant_id'" in tenant_sql
    assert tenant_params == {"tenant_id": TENANT_ID}
    assert "INSERT INTO provider_factor_snapshots" in insert_sql
    assert "ON CONFLICT (tenant_id, kind, provider_id, symbol, as_of)" in insert_sql
    assert insert_params["kind"] == "fundamentals"
    assert insert_params["symbol"] == "DEMODATA"
    assert insert_params["payload"] == fundamentals.to_dict()
    assert "FROM provider_universe_members" in universe_sql
    assert universe_params["tenant_id"] == TENANT_ID
    assert "FROM provider_factor_snapshots" in factor_sql
    assert factor_params["tenant_id"] == TENANT_ID
    assert "count(*)" in universe_count_sql
    assert universe_count_params == {
        "tenant_id": TENANT_ID,
        "provider_id": "configured_universe",
    }
    assert "count(*)" in factor_count_sql
    assert factor_count_params == {
        "tenant_id": TENANT_ID,
        "kind": "fundamentals",
        "provider_id": "configured_fundamentals",
    }
    assert stored_factor.to_dict() == fundamentals.to_dict()
    assert loaded_universe.to_dict() == universe.to_dict()
    assert loaded_factor.to_dict() == fundamentals.to_dict()
    assert universe_count == 3
    assert factor_count == 4
    assert connection.committed is True


def test_provider_data_store_uses_postgres_for_production_like_backend() -> None:
    store = build_provider_data_store(
        {
            "PORTFOLIO_STORAGE_BACKEND": "postgres",
            "PORTFOLIO_DATABASE_URL": "postgresql+psycopg://portfolio:secret@db:5432/portfolio_agentic",
            "PORTFOLIO_TENANT_ID": TENANT_ID,
        }
    )

    assert isinstance(store, PostgresProviderDataStore)
    assert store.storage_status() == {
        "status": "persisted",
        "backend": "postgres",
        "configured": True,
        "tenant_scoped": True,
    }
