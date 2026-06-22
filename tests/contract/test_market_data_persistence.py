from __future__ import annotations

import sqlite3

from portfolio_domain.market_data_store import (
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


def test_market_data_store_uses_sqlite_when_db_path_is_configured(
    monkeypatch,
    tmp_path,
) -> None:
    db_path = tmp_path / "configured-market-data.db"
    monkeypatch.setenv("MARKET_DATA_DB_PATH", str(db_path))

    store = build_market_data_store()

    assert isinstance(store, SQLiteMarketDataStore)
    assert db_path.exists()


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
