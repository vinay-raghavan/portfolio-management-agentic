from __future__ import annotations

import sqlite3

from portfolio_domain.paper_ledger import (
    SQLitePaperLedgerStore,
    build_paper_ledger_store,
)


def test_sqlite_paper_ledger_persists_orders_approvals_and_audit_events(tmp_path) -> None:
    db_path = tmp_path / "paper-ledger.db"
    store = SQLitePaperLedgerStore(db_path)

    order, approval, audit_event = store.create_order_proposal(
        strategy_id="strategy-persistent-paper",
        symbol="TATAMOTORS",
        side="buy",
        quantity=7,
        order_type="limit",
        requested_price=970.25,
    )

    reloaded = SQLitePaperLedgerStore(db_path)

    assert [item.order_id for item in reloaded.list_orders()] == [order.order_id]
    assert [item.approval_id for item in reloaded.approval_queue()] == [
        approval.approval_id
    ]
    assert [item.event_id for item in reloaded.audit_events()] == [
        audit_event.event_id
    ]
    persisted_order = reloaded.list_orders()[0]
    assert persisted_order.status == "pending_approval"
    assert persisted_order.filled_quantity == 0
    assert persisted_order.fill_ids == []
    assert persisted_order.requested_price == 970.25


def test_sqlite_paper_ledger_seeds_fixture_positions_once(tmp_path) -> None:
    db_path = tmp_path / "paper-ledger.db"
    first = SQLitePaperLedgerStore(db_path)
    second = SQLitePaperLedgerStore(db_path)

    assert [position.symbol for position in first.list_positions()] == [
        "TATAMOTORS",
        "SBIN",
    ]
    assert [position.symbol for position in second.list_positions()] == [
        "TATAMOTORS",
        "SBIN",
    ]


def test_sqlite_paper_ledger_schema_reserves_future_simulated_fills(tmp_path) -> None:
    db_path = tmp_path / "paper-ledger.db"
    SQLitePaperLedgerStore(db_path)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

    assert {
        "paper_orders",
        "paper_positions",
        "paper_fills",
        "approval_requests",
        "audit_events",
    }.issubset(table_names)


def test_paper_ledger_store_uses_sqlite_when_db_path_is_configured(
    monkeypatch,
    tmp_path,
) -> None:
    db_path = tmp_path / "configured-ledger.db"
    monkeypatch.setenv("PAPER_LEDGER_DB_PATH", str(db_path))

    store = build_paper_ledger_store()

    assert isinstance(store, SQLitePaperLedgerStore)
    assert db_path.exists()
