from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from portfolio_domain import (
    PaperBatchRequest,
    PaperExecutionGrant,
    PaperExecutionOrder,
    PaperExecutionPolicyCeiling,
    PostgresPaperExecutionStore,
    evaluate_paper_execution_order,
)


NOW = datetime(2026, 7, 27, 9, 15, tzinfo=timezone.utc)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
ADMIN_ID = "22222222-2222-2222-2222-222222222222"
ANALYST_ID = "33333333-3333-3333-3333-333333333333"
APPROVER_ID = "44444444-4444-4444-4444-444444444444"
POLICY_ID = "55555555-5555-5555-5555-555555555555"
BATCH_ID = "66666666-6666-6666-6666-666666666666"


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, sql: str, params: dict) -> None:
        self.executed.append((sql, params))


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


def _policy() -> PaperExecutionPolicyCeiling:
    return PaperExecutionPolicyCeiling(
        policy_id=POLICY_ID,
        tenant_id=TENANT_ID,
        created_by_actor_id=ADMIN_ID,
        name="Paper sandbox ceiling",
        status="enabled",
        permitted_strategies=("breakout-continuation",),
        permitted_symbols=("TATAMOTORS", "SBIN"),
        permitted_sides=("buy",),
        permitted_order_types=("market", "limit"),
        max_orders=3,
        max_quantity_per_order=10,
        max_notional_per_order=20_000,
        max_gross_notional=40_000,
        max_net_notional=40_000,
        max_loss_limit=2_500,
        max_drawdown_limit=3_000,
        slippage_bps=25,
        quote_freshness_seconds=30,
        market_hours_only=True,
        self_approval_permitted=False,
        valid_from=NOW - timedelta(minutes=1),
        valid_until=NOW + timedelta(hours=1),
    )


def _batch() -> PaperBatchRequest:
    return PaperBatchRequest(
        batch_request_id=BATCH_ID,
        tenant_id=TENANT_ID,
        requested_by_actor_id=ANALYST_ID,
        strategy_key="breakout-continuation",
        status="proposed",
        orders=(
            PaperExecutionOrder(
                symbol="TATAMOTORS",
                side="buy",
                quantity=5,
                order_type="market",
            ),
        ),
        context_refs=({"type": "research_document", "id": "doc-1"},),
        risk_summary={"paper_only": True, "live_trading": "forbidden"},
    )


def _store(cursor: _FakeCursor, connection: _FakeConnection) -> PostgresPaperExecutionStore:
    return PostgresPaperExecutionStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
        now=lambda: NOW,
    )


def test_migration_adds_explicit_policy_symbols_for_batch_execution() -> None:
    migration = Path(
        "infra/db/alembic/versions/20260727_0003_paper_execution_policy_symbols.py"
    ).read_text()

    assert 'revision = "20260727_0003"' in migration
    assert 'down_revision = "20260727_0002"' in migration
    assert "paper_execution_policy_ceilings" in migration
    assert "permitted_symbols" in migration
    assert "op.add_column" in migration
    assert "op.drop_column" in migration


def test_store_upserts_policy_ceiling_with_tenant_scope_symbols_and_no_defaults() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    stored = store.upsert_policy_ceiling(_policy())

    sql, params = cursor.executed[0]
    assert "INSERT INTO paper_execution_policy_ceilings" in sql
    assert "tenant_id" in sql
    assert "permitted_symbols" in sql
    assert "ON CONFLICT (id)" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["status"] == "enabled"
    assert params["permitted_symbols"] == ["TATAMOTORS", "SBIN"]
    assert params["limits"]["max_orders"] == 3
    assert params["freshness_requirements"] == {"quote_freshness_seconds": 30}
    assert stored.policy_id == POLICY_ID
    assert stored.configuration_complete is True
    assert connection.committed is True
    assert "access_token" not in str(params).lower()
    assert "fyers" not in str(params).lower()


def test_store_creates_paper_batch_request_without_live_provider_payloads() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    batch = store.create_batch_request(_batch())

    sql, params = cursor.executed[0]
    assert "INSERT INTO paper_batch_requests" in sql
    assert "tenant_id" in sql
    assert "requested_by_actor_id" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["requested_by_actor_id"] == ANALYST_ID
    assert params["orders"][0]["symbol"] == "TATAMOTORS"
    assert params["risk_summary"] == {"paper_only": True, "live_trading": "forbidden"}
    assert batch.batch_request_id == BATCH_ID
    assert connection.committed is True
    assert "access_token" not in str(params).lower()
    assert "fyers" not in str(params).lower()


def test_store_rejects_fyers_payloads_before_paper_batch_persistence() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)
    contaminated = PaperBatchRequest(
        batch_request_id=BATCH_ID,
        tenant_id=TENANT_ID,
        requested_by_actor_id=ANALYST_ID,
        strategy_key="breakout-continuation",
        status="proposed",
        orders=_batch().orders,
        context_refs=({"type": "fyers_snapshot", "id": "snapshot-1"},),
        risk_summary={"paper_only": True},
    )

    with pytest.raises(ValueError, match="secrets"):
        store.create_batch_request(contaminated)

    assert cursor.executed == []
    assert connection.committed is False


def test_store_issues_human_bound_grant_and_persists_scope_under_ceiling() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    grant = store.issue_grant(
        policy=_policy(),
        batch_request=_batch(),
        approved_by_actor_id=APPROVER_ID,
        expires_at=NOW + timedelta(minutes=10),
    )

    sql, params = cursor.executed[0]
    assert isinstance(grant, PaperExecutionGrant)
    assert "INSERT INTO paper_execution_grants" in sql
    assert "approved_by_actor_id" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["approved_by_actor_id"] == APPROVER_ID
    assert params["approved_by_actor_id"] != ANALYST_ID
    assert params["scope"]["symbols"] == ["TATAMOTORS"]
    assert params["scope"]["max_orders"] == 1
    assert params["reserved_capacity"]["order_count"] == 1
    assert "access_token" not in str(params).lower()
    assert "fyers" not in str(params).lower()
    assert connection.committed is True


def test_store_records_execution_decision_as_idempotent_paper_ledger_entry() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)
    policy = _policy()
    batch = _batch()
    grant = store.issue_grant(
        policy=policy,
        batch_request=batch,
        approved_by_actor_id=APPROVER_ID,
        expires_at=NOW + timedelta(minutes=10),
    )
    cursor.executed.clear()
    order = batch.orders[0]
    decision = evaluate_paper_execution_order(
        policy=policy,
        grant=grant,
        batch_request=batch,
        order=order,
        idempotency_key="idem-ok",
        quote_price=980.0,
        quote_as_of=NOW - timedelta(seconds=10),
        now=NOW,
        available_cash=100_000,
    )

    store.record_execution_decision(
        grant=grant,
        batch_request=batch,
        order=order,
        decision=decision,
        fill_price=980.0,
        exposure_after={"gross_notional": 4_900.0, "net_notional": 4_900.0},
    )

    sql, params = cursor.executed[0]
    assert "INSERT INTO paper_ledger_entries" in sql
    assert "ON CONFLICT (tenant_id, idempotency_key) DO NOTHING" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["grant_id"] == grant.grant_id
    assert params["batch_request_id"] == batch.batch_request_id
    assert params["idempotency_key"] == "idem-ok"
    assert params["entry_type"] == "paper_execution_decision"
    assert params["status"] == "accepted"
    assert params["fill"]["mode"] == "paper"
    assert params["decision"]["audit_event"]["event_type"] == "paper_execution_accepted"
    assert "live" not in str(params["fill"]).lower()
    assert "fyers" not in str(params).lower()
    assert "token" not in str(params).lower()
    assert connection.committed is True
