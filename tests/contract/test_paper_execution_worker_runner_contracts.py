from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from portfolio_domain import (
    DatabaseBackend,
    PaperBatchRequest,
    PaperExecutionOrder,
    PaperExecutionPolicyCeiling,
    PaperExecutionFairQueueRunner,
    PaperExecutionQueueProcessor,
    PaperExecutionQueueProcessorResult,
    PaperExecutionQueueRunner,
    PaperExecutionWorkItem,
    build_postgres_paper_execution_fair_worker,
    build_postgres_paper_execution_worker,
    issue_paper_execution_grant,
)


NOW = datetime(2026, 7, 27, 9, 15, tzinfo=timezone.utc)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
ADMIN_ID = "22222222-2222-2222-2222-222222222222"
ANALYST_ID = "33333333-3333-3333-3333-333333333333"
APPROVER_ID = "44444444-4444-4444-4444-444444444444"
POLICY_ID = "55555555-5555-5555-5555-555555555555"
BATCH_ID = "66666666-6666-6666-6666-666666666666"


class _FakeQueueStore:
    def __init__(self, work_items: list[PaperExecutionWorkItem]) -> None:
        self.work_items = work_items
        self.policy = _policy()
        self.batch = _batch()
        self.grant = issue_paper_execution_grant(
            policy=self.policy,
            batch_request=self.batch,
            approved_by_actor_id=APPROVER_ID,
            expires_at=NOW + timedelta(minutes=10),
            now=NOW,
            grant_id="77777777-7777-7777-7777-777777777777",
        )
        self.recorded_decisions: list[dict[str, Any]] = []
        self.completed: list[dict[str, Any]] = []

    def claim_next_execution_work_item(self, *, worker_id: str, now=None):
        for index, work_item in enumerate(self.work_items):
            if work_item.status != "queued":
                continue
            claimed = replace(
                work_item,
                status="claimed",
                claimed_by=worker_id,
                claimed_at=now or NOW,
                attempt_count=work_item.attempt_count + 1,
                updated_at=now or NOW,
            )
            self.work_items[index] = claimed
            return claimed
        return None

    def claim_execution_work_item(self, *, work_item_id: str, worker_id: str, now=None):
        for work_item in self.work_items:
            if work_item.work_item_id == work_item_id and work_item.status == "queued":
                return self.claim_next_execution_work_item(worker_id=worker_id, now=now)
        return None

    def get_grant(self, grant_id: str):
        return self.grant if grant_id == self.grant.grant_id else None

    def get_batch_request(self, batch_request_id: str):
        return self.batch if batch_request_id == self.batch.batch_request_id else None

    def get_policy_ceiling(self, policy_id: str):
        return self.policy if policy_id == self.policy.policy_id else None

    def execution_decision_exists(self, idempotency_key: str) -> bool:
        return False

    def record_execution_decision(
        self,
        *,
        grant,
        batch_request,
        order,
        decision,
        fill_price: float,
        exposure_after,
    ):
        self.recorded_decisions.append(
            {
                "grant_id": grant.grant_id,
                "batch_request_id": batch_request.batch_request_id,
                "symbol": order.symbol,
                "decision": decision.to_dict(),
                "fill_price": fill_price,
                "exposure_after": dict(exposure_after),
            }
        )
        return decision

    def complete_execution_work_item(self, *, work_item_id: str, decision, now=None):
        for index, work_item in enumerate(self.work_items):
            if work_item.work_item_id != work_item_id:
                continue
            status = "completed" if decision.status == "accepted" else "failed"
            completed = replace(
                work_item,
                status=status,
                decision=decision.to_dict(),
                completed_at=now or NOW,
                updated_at=now or NOW,
            )
            self.work_items[index] = completed
            self.completed.append(
                {
                    "work_item_id": work_item_id,
                    "status": status,
                    "decision": decision.to_dict(),
                }
            )
            return completed
        return None


class _ScriptedProcessor:
    def __init__(
        self,
        *,
        worker_id: str,
        statuses: list[str],
        call_order: list[str],
    ) -> None:
        self.worker_id = worker_id
        self.statuses = statuses
        self.call_order = call_order

    def process_once(self, *, work_item_id=None):
        self.call_order.append(self.worker_id)
        if not self.statuses:
            return PaperExecutionQueueProcessorResult(
                status="no_work",
                work_item_id=work_item_id,
                decision=None,
            )
        return PaperExecutionQueueProcessorResult(
            status=self.statuses.pop(0),
            work_item_id=work_item_id or f"work-{self.worker_id}",
            decision=None,
        )


def _policy() -> PaperExecutionPolicyCeiling:
    return PaperExecutionPolicyCeiling(
        policy_id=POLICY_ID,
        tenant_id=TENANT_ID,
        created_by_actor_id=ADMIN_ID,
        name="Paper sandbox ceiling",
        status="enabled",
        permitted_strategies=("breakout-continuation",),
        permitted_symbols=("TATAMOTORS",),
        permitted_sides=("buy",),
        permitted_order_types=("market",),
        max_orders=2,
        max_quantity_per_order=5,
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
            PaperExecutionOrder(
                symbol="TATAMOTORS",
                side="buy",
                quantity=4,
                order_type="market",
            ),
        ),
        context_refs=({"type": "research_document", "id": "doc-1"},),
        risk_summary={"paper_only": True, "live_trading": "forbidden"},
    )


def _work_item(index: int, **overrides: Any) -> PaperExecutionWorkItem:
    values = {
        "work_item_id": f"88888888-8888-8888-8888-88888888888{index}",
        "tenant_id": TENANT_ID,
        "batch_request_id": BATCH_ID,
        "grant_id": "77777777-7777-7777-7777-777777777777",
        "order_id": f"{BATCH_ID}:{index}",
        "requested_by_actor_id": ANALYST_ID,
        "idempotency_key": f"idem-worker-runner-{index}",
        "status": "queued",
        "payload": {
            "schema_version": "paper-execution-work-item/v1",
            "quote_price": 980,
            "quote_as_of": (NOW - timedelta(seconds=10)).isoformat(),
            "now": NOW.isoformat(),
            "available_cash": 100_000,
            "kill_switch_active": False,
            "exposure_after": {"gross_notional": 4_900.0, "net_notional": 4_900.0},
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


def _runner_for(store: _FakeQueueStore) -> PaperExecutionQueueRunner:
    return PaperExecutionQueueRunner(
        processor=PaperExecutionQueueProcessor(
            store=store,
            worker_id="paper-execution-worker",
            now=lambda: NOW,
        )
    )


def test_worker_runner_processes_until_idle_without_model_visible_authority() -> None:
    store = _FakeQueueStore([_work_item(0), _work_item(1)])
    runner = _runner_for(store)

    summary = runner.run_until_idle(max_items=5)

    assert summary.to_dict() == {
        "schema_version": "paper-execution-worker-runner-summary/v1",
        "processed": 2,
        "failed": 0,
        "idle": True,
        "total_attempted": 2,
        "worker_id": "paper-execution-worker",
    }
    assert [item.status for item in store.work_items] == ["completed", "completed"]
    assert len(store.recorded_decisions) == 2
    assert "approve" not in str(summary.to_dict()).lower()
    assert "fyers" not in str(summary.to_dict()).lower()


def test_worker_runner_counts_fail_closed_items_and_stops_at_budget() -> None:
    malformed = _work_item(
        0,
        payload={"schema_version": "paper-execution-work-item/v1"},
    )
    store = _FakeQueueStore([malformed, _work_item(1)])
    runner = _runner_for(store)

    summary = runner.run_until_idle(max_items=1)

    assert summary.processed == 0
    assert summary.failed == 1
    assert summary.idle is False
    assert summary.total_attempted == 1
    assert store.work_items[0].status == "failed"
    assert store.work_items[1].status == "queued"
    assert store.recorded_decisions == []


def test_postgres_worker_factory_requires_postgres_storage() -> None:
    with pytest.raises(ValueError, match="postgres_storage_required"):
        build_postgres_paper_execution_worker(
            tenant_id=TENANT_ID,
            database_url=None,
            backend=DatabaseBackend.SQLITE,
        )


def test_fair_worker_runner_processes_tenants_round_robin() -> None:
    call_order: list[str] = []
    runner = PaperExecutionFairQueueRunner(
        processors=(
            _ScriptedProcessor(
                worker_id="paper-worker:tenant-a",
                statuses=["processed", "processed", "processed"],
                call_order=call_order,
            ),
            _ScriptedProcessor(
                worker_id="paper-worker:tenant-b",
                statuses=["processed"],
                call_order=call_order,
            ),
        )
    )

    summary = runner.run_until_idle(max_items=3)

    assert call_order == [
        "paper-worker:tenant-a",
        "paper-worker:tenant-b",
        "paper-worker:tenant-a",
    ]
    assert summary.to_dict() == {
        "schema_version": "paper-execution-fair-worker-runner-summary/v1",
        "processed": 3,
        "failed": 0,
        "idle": False,
        "total_attempted": 3,
        "worker_ids": ["paper-worker:tenant-a", "paper-worker:tenant-b"],
        "per_worker": [
            {
                "worker_id": "paper-worker:tenant-a",
                "processed": 2,
                "failed": 0,
                "idle": False,
                "total_attempted": 2,
            },
            {
                "worker_id": "paper-worker:tenant-b",
                "processed": 1,
                "failed": 0,
                "idle": False,
                "total_attempted": 1,
            },
        ],
    }


def test_fair_worker_runner_reports_idle_only_after_every_tenant_is_idle() -> None:
    call_order: list[str] = []
    runner = PaperExecutionFairQueueRunner(
        processors=(
            _ScriptedProcessor(
                worker_id="paper-worker:tenant-a",
                statuses=["no_work"],
                call_order=call_order,
            ),
            _ScriptedProcessor(
                worker_id="paper-worker:tenant-b",
                statuses=["failed", "no_work"],
                call_order=call_order,
            ),
        )
    )

    summary = runner.run_until_idle(max_items=5)

    assert call_order == [
        "paper-worker:tenant-a",
        "paper-worker:tenant-b",
        "paper-worker:tenant-b",
    ]
    assert summary.processed == 0
    assert summary.failed == 1
    assert summary.idle is True
    assert summary.total_attempted == 1


def test_postgres_fair_worker_factory_requires_at_least_one_tenant() -> None:
    with pytest.raises(ValueError, match="tenant_id_required"):
        build_postgres_paper_execution_fair_worker(
            tenant_ids=(),
            database_url="postgresql+psycopg://portfolio:secret@postgres/db",
            backend=DatabaseBackend.POSTGRES,
        )
