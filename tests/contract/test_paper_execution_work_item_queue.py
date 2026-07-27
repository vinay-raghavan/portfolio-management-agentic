from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from portfolio_domain import (
    PaperExecutionDecision,
    PaperExecutionWorkItem,
    PostgresPaperExecutionStore,
)


NOW = datetime(2026, 7, 27, 9, 15, tzinfo=timezone.utc)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
WORK_ITEM_ID = "22222222-2222-2222-2222-222222222222"
BATCH_ID = "33333333-3333-3333-3333-333333333333"
GRANT_ID = "44444444-4444-4444-4444-444444444444"
ANALYST_ID = "55555555-5555-5555-5555-555555555555"
IDEMPOTENCY_KEY = "paper-exec-queue-1"


class _FakeCursor:
    def __init__(
        self,
        *,
        rows: list[tuple] | None = None,
        columns: list[str] | None = None,
    ) -> None:
        self.executed: list[tuple[str, dict[str, Any]]] = []
        self._rows = rows or []
        self.description = [(column,) for column in columns or []]

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, sql: str, params: dict[str, Any]) -> None:
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


def _store(cursor: _FakeCursor, connection: _FakeConnection) -> PostgresPaperExecutionStore:
    return PostgresPaperExecutionStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
        now=lambda: NOW,
    )


def _work_item(**overrides: Any) -> PaperExecutionWorkItem:
    values = {
        "work_item_id": WORK_ITEM_ID,
        "tenant_id": TENANT_ID,
        "batch_request_id": BATCH_ID,
        "grant_id": GRANT_ID,
        "order_id": f"{BATCH_ID}:0",
        "requested_by_actor_id": ANALYST_ID,
        "idempotency_key": IDEMPOTENCY_KEY,
        "status": "queued",
        "payload": {
            "schema_version": "paper-execution-work-item/v1",
            "quote_price": 102.4,
            "quote_as_of": NOW.isoformat(),
            "available_cash": 50_000,
        },
        "decision": None,
        "attempt_count": 0,
        "available_at": NOW,
        "claimed_by": None,
        "claimed_at": None,
        "completed_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return PaperExecutionWorkItem(**values)


def _work_item_columns() -> list[str]:
    return [
        "id",
        "tenant_id",
        "batch_request_id",
        "grant_id",
        "order_id",
        "requested_by_actor_id",
        "idempotency_key",
        "status",
        "payload",
        "decision",
        "attempt_count",
        "available_at",
        "claimed_by",
        "claimed_at",
        "completed_at",
        "created_at",
        "updated_at",
    ]


def _work_item_row(**overrides: Any) -> tuple[Any, ...]:
    item = _work_item(**overrides)
    return (
        item.work_item_id,
        item.tenant_id,
        item.batch_request_id,
        item.grant_id,
        item.order_id,
        item.requested_by_actor_id,
        item.idempotency_key,
        item.status,
        item.payload,
        item.decision,
        item.attempt_count,
        item.available_at,
        item.claimed_by,
        item.claimed_at,
        item.completed_at,
        item.created_at,
        item.updated_at,
    )


def _decision(status: str = "accepted") -> PaperExecutionDecision:
    return PaperExecutionDecision(
        status=status,
        reasons=("simulated_fill_recorded",) if status == "accepted" else ("stale_quote",),
        fill={"symbol": "TATAMOTORS", "quantity": 5, "price": 102.4}
        if status == "accepted"
        else None,
        audit_event={
            "event_type": "paper_execution_decision",
            "idempotency_key": IDEMPOTENCY_KEY,
            "notional": 512.0,
        },
    )


def test_migration_adds_tenant_scoped_paper_execution_work_item_queue() -> None:
    migration = Path(
        "infra/db/alembic/versions/20260727_0004_paper_execution_work_items.py"
    ).read_text()

    assert 'revision = "20260727_0004"' in migration
    assert 'down_revision = "20260727_0003"' in migration
    assert '"paper_execution_work_items"' in migration
    assert "paper_execution_grants.id" in migration
    assert "paper_batch_requests.id" in migration
    assert "uq_paper_execution_work_items_tenant_idempotency_key" in migration
    assert "ck_paper_execution_work_items_status" in migration
    assert "queued" in migration
    assert "claimed" in migration
    assert "completed" in migration
    assert "failed" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "DROP POLICY IF EXISTS" in migration
    assert "tenant_isolation_{table_name}" in migration


def test_store_enqueues_paper_execution_work_item_without_live_provider_payloads() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    stored = store.enqueue_execution_work_item(_work_item())

    sql, params = cursor.executed[0]
    assert "INSERT INTO paper_execution_work_items" in sql
    assert "tenant_id" in sql
    assert "idempotency_key" in sql
    assert "ON CONFLICT (tenant_id, idempotency_key) DO NOTHING" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["status"] == "queued"
    assert params["payload"]["schema_version"] == "paper-execution-work-item/v1"
    assert params["attempt_count"] == 0
    assert stored.work_item_id == WORK_ITEM_ID
    assert connection.committed is True
    assert "access_token" not in str(params).lower()
    assert "fyers" not in str(params).lower()


def test_store_rejects_sensitive_work_item_payload_before_enqueue() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    with pytest.raises(ValueError, match="secrets"):
        store.enqueue_execution_work_item(
            _work_item(payload={"schema_version": "paper-execution-work-item/v1", "access_token": "x"})
        )

    assert cursor.executed == []
    assert connection.committed is False


def test_store_claims_next_work_item_with_skip_locked_and_tenant_scope() -> None:
    cursor = _FakeCursor(
        rows=[
            _work_item_row(
                status="claimed",
                attempt_count=1,
                claimed_by="paper-worker-1",
                claimed_at=NOW,
                updated_at=NOW,
            )
        ],
        columns=_work_item_columns(),
    )
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    claimed = store.claim_next_execution_work_item(worker_id="paper-worker-1", now=NOW)

    assert claimed is not None
    sql, params = cursor.executed[0]
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "status = 'queued'" in sql
    assert "available_at <= %(now)s" in sql
    assert "attempt_count = paper_execution_work_items.attempt_count + 1" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["worker_id"] == "paper-worker-1"
    assert claimed.status == "claimed"
    assert claimed.claimed_by == "paper-worker-1"
    assert claimed.attempt_count == 1
    assert connection.committed is True


def test_store_claims_specific_work_item_with_skip_locked_and_tenant_scope() -> None:
    cursor = _FakeCursor(
        rows=[
            _work_item_row(
                status="claimed",
                attempt_count=1,
                claimed_by="paper-worker-1",
                claimed_at=NOW,
                updated_at=NOW,
            )
        ],
        columns=_work_item_columns(),
    )
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    claimed = store.claim_execution_work_item(
        work_item_id=WORK_ITEM_ID,
        worker_id="paper-worker-1",
        now=NOW,
    )

    assert claimed is not None
    sql, params = cursor.executed[0]
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "id = %(work_item_id)s" in sql
    assert "status = 'queued'" in sql
    assert "attempt_count = paper_execution_work_items.attempt_count + 1" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["work_item_id"] == WORK_ITEM_ID
    assert params["worker_id"] == "paper-worker-1"
    assert claimed.status == "claimed"
    assert claimed.work_item_id == WORK_ITEM_ID
    assert connection.committed is True


def test_store_completes_work_item_with_redacted_decision_payload() -> None:
    decision = _decision()
    cursor = _FakeCursor(
        rows=[
            _work_item_row(
                status="completed",
                decision=decision.to_dict(),
                completed_at=NOW,
                updated_at=NOW,
            )
        ],
        columns=_work_item_columns(),
    )
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    completed = store.complete_execution_work_item(
        work_item_id=WORK_ITEM_ID,
        decision=decision,
        now=NOW,
    )

    assert completed is not None
    sql, params = cursor.executed[0]
    assert "UPDATE paper_execution_work_items" in sql
    assert "WHERE tenant_id = %(tenant_id)s" in sql
    assert "AND id = %(work_item_id)s" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["status"] == "completed"
    assert params["decision"]["status"] == "accepted"
    assert completed.status == "completed"
    assert completed.decision is not None
    assert completed.decision["status"] == "accepted"
    assert completed.decision["audit_event"]["idempotency_key"] == IDEMPOTENCY_KEY
    assert connection.committed is True
    assert "access_token" not in str(params).lower()
    assert "fyers" not in str(params).lower()
