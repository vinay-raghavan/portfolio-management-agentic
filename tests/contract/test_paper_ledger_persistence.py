from __future__ import annotations

import sqlite3
from pathlib import Path

from portfolio_domain.paper_ledger import (
    PaperLedgerStore,
    PostgresPaperLedgerStore,
    SQLitePaperLedgerStore,
    build_paper_ledger_store,
)


def _ready_preflight(symbol: str = "TATAMOTORS") -> dict:
    return {
        "schema_version": "paper-order-readiness-preflight/v1",
        "status": "ready_for_approval",
        "mode": "paper_only",
        "evaluated_at": "2026-06-22T09:15:00+05:30",
        "strategy_id": f"strategy-{symbol.lower()}",
        "symbol": symbol,
        "setup": "breakout-continuation",
        "recommendation": {"stance": "paper_draft_candidate"},
        "provider_import_reconciliation": {"status": "pass"},
        "provider_refresh_readiness": {"status": "pass"},
        "history": {"strategy_ids": [], "backtest_request_ids": []},
        "risk_gates": [],
        "paper_only_policy": {
            "live_trading": "disabled",
            "broker_token_access": "forbidden",
            "simulated_fills": "approval_required",
        },
        "required_approval": "human",
        "blocking_reasons": [],
    }


def test_sqlite_paper_ledger_persists_orders_approvals_and_audit_events(
    tmp_path,
) -> None:
    db_path = tmp_path / "paper-ledger.db"
    store = SQLitePaperLedgerStore(db_path)

    order, approval, audit_event = store.create_order_proposal(
        strategy_id="strategy-persistent-paper",
        symbol="TATAMOTORS",
        side="buy",
        quantity=7,
        order_type="limit",
        requested_price=970.25,
        readiness_preflight=_ready_preflight(),
    )

    reloaded = SQLitePaperLedgerStore(db_path)

    assert [item.order_id for item in reloaded.list_orders()] == [order.order_id]
    assert [item.approval_id for item in reloaded.approval_queue()] == [
        approval.approval_id
    ]
    assert [item.event_id for item in reloaded.audit_events()] == [audit_event.event_id]
    persisted_order = reloaded.list_orders()[0]
    assert persisted_order.status == "pending_approval"
    assert persisted_order.filled_quantity == 0
    assert persisted_order.fill_ids == []
    assert persisted_order.requested_price == 970.25
    assert persisted_order.readiness_preflight["status"] == "ready_for_approval"
    assert persisted_order.readiness_preflight["required_approval"] == "human"


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


def test_sqlite_paper_ledger_schema_includes_simulated_fills(tmp_path) -> None:
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
        "strategy_drafts",
        "backtest_requests",
        "paper_orders",
        "paper_positions",
        "paper_fills",
        "approval_requests",
        "audit_events",
    }.issubset(table_names)


def test_sqlite_paper_ledger_persists_strategy_and_backtest_history(tmp_path) -> None:
    db_path = tmp_path / "paper-ledger.db"
    store = SQLitePaperLedgerStore(db_path)

    strategy = store.create_strategy_draft(
        "TATAMOTORS",
        "Top ranked fixture candidate with evidence-backed paper setup.",
    )
    backtest_request = store.create_backtest_request(
        "TATAMOTORS",
        "breakout-continuation",
        "2026-01-02",
        "2026-06-22",
    )

    reloaded = SQLitePaperLedgerStore(db_path)
    backtest_result = reloaded.get_backtest_result(backtest_request.request_id)

    assert [item.strategy_id for item in reloaded.list_strategy_drafts()] == [
        strategy.strategy_id
    ]
    assert reloaded.get_strategy_draft(strategy.strategy_id) == strategy
    assert [item.request_id for item in reloaded.list_backtest_requests()] == [
        backtest_request.request_id
    ]
    assert (
        reloaded.get_backtest_request(backtest_request.request_id) == backtest_request
    )
    assert backtest_result.request_id == backtest_request.request_id
    assert backtest_result.status == "simulated"
    assert backtest_result.mode == "paper"


def test_paper_ledger_store_uses_sqlite_when_db_path_is_configured(
    monkeypatch,
    tmp_path,
) -> None:
    db_path = tmp_path / "configured-ledger.db"
    monkeypatch.setenv("PAPER_LEDGER_DB_PATH", str(db_path))

    store = build_paper_ledger_store()

    assert isinstance(store, SQLitePaperLedgerStore)
    assert db_path.exists()


TENANT_ID = "11111111-1111-1111-1111-111111111111"


class _FakeCursor:
    def __init__(self, rows: list[dict | list[dict] | None] | None = None) -> None:
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
        row = self._rows.pop(0)
        if row is None:
            return None
        if isinstance(row, list):
            raise AssertionError(f"Expected one row, got row batch: {row}")
        return row

    def fetchall(self):
        if not self._rows:
            return []
        rows = self._rows.pop(0)
        if rows is None:
            return []
        if isinstance(rows, list):
            return rows
        return [rows]


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


def test_migration_adds_tenant_scoped_paper_ledger_tables() -> None:
    migration = Path(
        "infra/db/alembic/versions/20260727_0010_paper_ledger_store.py"
    ).read_text()

    assert 'revision = "20260727_0010"' in migration
    assert 'down_revision = "20260727_0009"' in migration
    for table in (
        "paper_strategy_drafts",
        "paper_backtest_requests",
        "paper_orders",
        "paper_positions",
        "paper_fills",
        "paper_approval_requests",
        "paper_audit_events",
    ):
        assert table in migration
    assert "tenant_id" in migration
    assert "payload" in migration
    assert "jsonb" in migration.lower()
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "tenant_isolation_{table_name}" in migration
    assert "DROP POLICY IF EXISTS" in migration
    assert "broker_token" not in migration
    assert "access_token" not in migration


def test_postgres_paper_ledger_records_strategy_and_backtest_history() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = PostgresPaperLedgerStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
    )

    strategy = store.create_strategy_draft(
        "TATAMOTORS",
        "Tenant-scoped Postgres paper strategy contract.",
    )
    request = store.create_backtest_request(
        "TATAMOTORS",
        "breakout-continuation",
        "2026-01-02",
        "2026-06-22",
    )

    strategy_sql, strategy_params = cursor.executed[1]
    backtest_sql, backtest_params = cursor.executed[3]
    serialized = f"{cursor.executed}".lower()
    assert "set_config('app.tenant_id'" in cursor.executed[0][0]
    assert cursor.executed[0][1] == {"tenant_id": TENANT_ID}
    assert "INSERT INTO paper_strategy_drafts" in strategy_sql
    assert "ON CONFLICT (tenant_id, strategy_id)" in strategy_sql
    assert strategy_params["tenant_id"] == TENANT_ID
    assert strategy_params["payload"] == strategy.to_dict()
    assert "INSERT INTO paper_backtest_requests" in backtest_sql
    assert "ON CONFLICT (tenant_id, request_id)" in backtest_sql
    assert backtest_params["tenant_id"] == TENANT_ID
    assert backtest_params["payload"] == request.to_dict()
    assert connection.committed is True
    assert "paper-ledger.db" not in serialized
    assert "broker_token" not in serialized
    assert "access_token" not in serialized


def test_postgres_paper_ledger_reads_and_mutates_approval_fill_workflow() -> None:
    setup_store = PaperLedgerStore()
    order, approval, proposal_event = setup_store.create_order_proposal(
        strategy_id="strategy-postgres-paper",
        symbol="TATAMOTORS",
        side="buy",
        quantity=3,
        order_type="limit",
        requested_price=970.25,
        readiness_preflight=_ready_preflight(),
    )
    approved_order, approved_approval, _ = setup_store.approve_order_simulation(
        order.order_id,
        "human-review",
        "Postgres contract approval.",
    )
    fill, filled_order, position, fill_event = setup_store.simulate_approved_fill(
        order.order_id,
        970.25,
    )
    fixture_position = next(
        item for item in PaperLedgerStore().list_positions() if item.symbol == order.symbol
    )
    cursor = _FakeCursor(
        rows=[
            {"payload": order.to_dict()},
            {"payload": approval.to_dict()},
            {"payload": approved_order.to_dict()},
            {"payload": approved_approval.to_dict()},
            None,
            {"payload": fixture_position.to_dict()},
            [{"payload": filled_order.to_dict()}],
            None,
            [{"payload": fill.to_dict()}],
            [{"payload": position.to_dict()}],
            [{"payload": proposal_event.to_dict()}],
        ]
    )
    connection = _FakeConnection(cursor)
    store = PostgresPaperLedgerStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
    )

    approved_result, approval_result, _ = store.approve_order_simulation(
        order.order_id,
        "human-review",
        "Postgres contract approval.",
    )
    fill_result, filled_order_result, position_result, event_result = (
        store.simulate_approved_fill(order.order_id, fill_price=970.25)
    )
    orders = store.list_orders()
    approvals = store.approval_queue()
    fills = store.list_fills()
    positions = store.list_positions()
    audit_events = store.audit_events()

    assert approved_result.status == "approved"
    assert approval_result.status == "approved"
    assert fill_result.to_dict() == fill.to_dict()
    assert filled_order_result.status == "filled"
    assert position_result.to_dict() == position.to_dict()
    assert event_result.to_dict() == fill_event.to_dict()
    assert [item.to_dict() for item in orders] == [filled_order.to_dict()]
    assert approvals == []
    assert [item.to_dict() for item in fills] == [fill.to_dict()]
    assert {item.symbol for item in positions} == {"SBIN", position.symbol}
    assert any(item.to_dict() == position.to_dict() for item in positions)
    assert [item.to_dict() for item in audit_events] == [proposal_event.to_dict()]
    assert all(
        "tenant_id = %(tenant_id)s" in sql
        for sql, _ in cursor.executed
        if "FROM paper_" in sql
    )


def test_paper_ledger_store_uses_postgres_for_production_like_backend() -> None:
    store = build_paper_ledger_store(
        {
            "PORTFOLIO_STORAGE_BACKEND": "postgres",
            "PORTFOLIO_DATABASE_URL": "postgresql+psycopg://portfolio:secret@db:5432/portfolio_agentic",
            "PORTFOLIO_TENANT_ID": TENANT_ID,
        }
    )

    assert isinstance(store, PostgresPaperLedgerStore)
    assert store.storage_status() == {
        "status": "persisted",
        "backend": "postgres",
        "configured": True,
        "tenant_scoped": True,
    }
