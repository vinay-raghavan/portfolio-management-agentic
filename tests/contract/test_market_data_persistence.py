from __future__ import annotations

import sqlite3
from pathlib import Path

from portfolio_domain.market_data_store import (
    PostgresMarketDataStore,
    SQLiteMarketDataStore,
    build_market_data_store,
)
from portfolio_domain.product_data import run_fixture_screener
from portfolio_domain.providers import FixtureMarketDataProvider
from portfolio_mcp.tools import (
    get_market_data_snapshot,
    list_market_data_snapshots,
    list_screener_runs,
    run_screener,
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

    def fetchall(self):
        rows = self._rows
        self._rows = []
        return rows


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


def test_sqlite_market_data_store_persists_snapshots_in_provider_shape(
    tmp_path,
) -> None:
    db_path = tmp_path / "market-data.db"
    snapshot = FixtureMarketDataProvider().get_snapshot("TATAMOTORS")

    store = SQLiteMarketDataStore(db_path)
    store.record_market_snapshot(snapshot)

    reloaded = SQLiteMarketDataStore(db_path)

    assert reloaded.get_market_snapshot("TATAMOTORS").to_dict() == snapshot.to_dict()
    assert [
        item.to_dict() for item in reloaded.list_market_snapshots("TATAMOTORS")
    ] == [snapshot.to_dict()]


def test_sqlite_market_data_store_persists_screener_runs_in_tool_shape(
    tmp_path,
) -> None:
    db_path = tmp_path / "market-data.db"
    screener_run = run_fixture_screener("fixture_nifty50", "momentum", 3)

    store = SQLiteMarketDataStore(db_path)
    store.record_screener_run(screener_run)

    reloaded = SQLiteMarketDataStore(db_path)

    assert reloaded.get_screener_run(screener_run.run_id).to_dict() == screener_run.to_dict()
    assert [
        item.to_dict()
        for item in reloaded.list_screener_runs("fixture_nifty50", "momentum")
    ] == [screener_run.to_dict()]


def test_sqlite_market_data_store_schema_is_separate_from_paper_ledger(
    tmp_path,
) -> None:
    db_path = tmp_path / "market-data.db"
    SQLiteMarketDataStore(db_path)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

    assert {
        "market_data_snapshots",
        "screener_runs",
    }.issubset(table_names)
    assert "paper_orders" not in table_names


def test_migration_adds_tenant_scoped_market_data_and_screener_tables() -> None:
    migration = Path(
        "infra/db/alembic/versions/20260727_0007_market_data_screener_store.py"
    ).read_text()

    assert 'revision = "20260727_0007"' in migration
    assert 'down_revision = "20260727_0006"' in migration
    assert "market_data_snapshots" in migration
    assert "screener_runs" in migration
    assert "tenant_id" in migration
    assert "payload" in migration
    assert "jsonb" in migration.lower()
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "tenant_isolation_{table_name}" in migration
    assert "DROP POLICY IF EXISTS" in migration
    assert "access_token" not in migration
    assert "credential" not in migration


def test_postgres_market_data_store_records_tenant_scoped_snapshot_without_paths() -> None:
    snapshot = FixtureMarketDataProvider().get_snapshot("TATAMOTORS")
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = PostgresMarketDataStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
    )

    stored = store.record_market_snapshot(snapshot)

    tenant_sql, tenant_params = cursor.executed[0]
    sql, params = cursor.executed[1]
    serialized = f"{sql} {params}".lower()
    assert "set_config('app.tenant_id'" in tenant_sql
    assert tenant_params == {"tenant_id": TENANT_ID}
    assert "INSERT INTO market_data_snapshots" in sql
    assert "tenant_id" in sql
    assert "ON CONFLICT (tenant_id, provider_id, symbol, as_of)" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["provider_id"] == snapshot.provider_id
    assert params["symbol"] == "TATAMOTORS"
    assert params["payload"] == snapshot.to_dict()
    assert stored.to_dict() == snapshot.to_dict()
    assert connection.committed is True
    assert "market-data.db" not in serialized
    assert "access_token" not in serialized
    assert "secret" not in serialized


def test_postgres_market_data_store_reads_snapshots_and_screener_runs() -> None:
    snapshot = FixtureMarketDataProvider().get_snapshot("TATAMOTORS")
    screener_run = run_fixture_screener("fixture_nifty50", "momentum", 3)
    cursor = _FakeCursor(
        rows=[
            {"payload": snapshot.to_dict()},
            {"payload": screener_run.to_dict()},
            {"row_count": 7},
        ]
    )
    connection = _FakeConnection(cursor)
    store = PostgresMarketDataStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
    )

    assert store.get_market_snapshot("TATAMOTORS").to_dict() == snapshot.to_dict()
    assert store.get_screener_run(screener_run.run_id).to_dict() == screener_run.to_dict()
    assert store.count_market_snapshots(snapshot.provider_id) == 7

    snapshot_tenant_sql, snapshot_tenant_params = cursor.executed[0]
    snapshot_sql, snapshot_params = cursor.executed[1]
    run_tenant_sql, run_tenant_params = cursor.executed[2]
    run_sql, run_params = cursor.executed[3]
    count_tenant_sql, count_tenant_params = cursor.executed[4]
    count_sql, count_params = cursor.executed[5]
    assert "set_config('app.tenant_id'" in snapshot_tenant_sql
    assert snapshot_tenant_params == {"tenant_id": TENANT_ID}
    assert "set_config('app.tenant_id'" in run_tenant_sql
    assert run_tenant_params == {"tenant_id": TENANT_ID}
    assert "set_config('app.tenant_id'" in count_tenant_sql
    assert count_tenant_params == {"tenant_id": TENANT_ID}
    assert "FROM market_data_snapshots" in snapshot_sql
    assert "tenant_id = %(tenant_id)s" in snapshot_sql
    assert snapshot_params["symbol"] == "TATAMOTORS"
    assert "FROM screener_runs" in run_sql
    assert "tenant_id = %(tenant_id)s" in run_sql
    assert run_params["run_id"] == screener_run.run_id
    assert "count(*)" in count_sql
    assert count_params == {"tenant_id": TENANT_ID, "provider_id": snapshot.provider_id}


def test_market_data_store_uses_sqlite_when_db_path_is_configured(
    monkeypatch,
    tmp_path,
) -> None:
    db_path = tmp_path / "configured-market-data.db"
    monkeypatch.setenv("MARKET_DATA_DB_PATH", str(db_path))

    store = build_market_data_store()

    assert isinstance(store, SQLiteMarketDataStore)
    assert db_path.exists()


def test_market_data_store_uses_postgres_for_production_like_backend() -> None:
    store = build_market_data_store(
        {
            "PORTFOLIO_STORAGE_BACKEND": "postgres",
            "PORTFOLIO_DATABASE_URL": "postgresql+psycopg://portfolio:secret@db:5432/portfolio_agentic",
            "PORTFOLIO_TENANT_ID": TENANT_ID,
        }
    )

    assert isinstance(store, PostgresMarketDataStore)
    assert store.storage_status() == {
        "status": "persisted",
        "backend": "postgres",
        "configured": True,
        "tenant_scoped": True,
    }


def test_market_data_tools_report_storage_without_paths_or_credentials() -> None:
    snapshot = get_market_data_snapshot("TATAMOTORS")
    screener = run_screener("fixture_nifty50", "momentum", 3)
    snapshots = list_market_data_snapshots("TATAMOTORS", 5)
    screener_runs = list_screener_runs("fixture_nifty50", "momentum", 5)

    assert snapshot["status"] == "success"
    assert snapshot["policy"]["tier"] == "read_only"
    assert snapshot["storage"]["status"] in {"memory", "persisted"}
    assert snapshot["snapshot"]["source"] == "offline_fixture"

    assert screener["status"] == "success"
    assert screener["policy"]["tier"] == "read_only"
    assert screener["storage"]["status"] in {"memory", "persisted"}
    assert screener["screener_run"]["run_summary"]["providers_used"]["market_data"]

    assert snapshots["policy"]["tier"] == "read_only"
    assert snapshots["snapshots"][0]["symbol"] == "TATAMOTORS"
    assert screener_runs["policy"]["tier"] == "read_only"
    assert screener_runs["screener_runs"][0]["run_id"] == screener["screener_run"]["run_id"]

    combined = f"{snapshot} {screener} {snapshots} {screener_runs}".lower()
    assert "market-data.db" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
