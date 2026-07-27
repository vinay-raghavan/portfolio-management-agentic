from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

from portfolio_domain import (
    PaperBatchRequest,
    PaperExecutionOrder,
    PaperExecutionPolicyCeiling,
    PaperExecutionQueueProcessor,
    PaperExecutionWorkItem,
    issue_paper_execution_grant,
)


NOW = datetime(2026, 7, 27, 9, 15, tzinfo=timezone.utc)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
ADMIN_ID = "22222222-2222-2222-2222-222222222222"
ANALYST_ID = "33333333-3333-3333-3333-333333333333"
APPROVER_ID = "44444444-4444-4444-4444-444444444444"
POLICY_ID = "55555555-5555-5555-5555-555555555555"
BATCH_ID = "66666666-6666-6666-6666-666666666666"
GRANT_ID = "77777777-7777-7777-7777-777777777777"
WORK_ITEM_ID = "88888888-8888-8888-8888-888888888888"


class _FakeQueueStore:
    def __init__(
        self,
        *,
        work_item: PaperExecutionWorkItem | None = None,
        policy: PaperExecutionPolicyCeiling | None = None,
        batch: PaperBatchRequest | None = None,
    ) -> None:
        self.work_item = work_item
        self.policy = policy or _policy()
        self.batch = batch or _batch()
        self.grant = issue_paper_execution_grant(
            policy=self.policy,
            batch_request=self.batch,
            approved_by_actor_id=APPROVER_ID,
            expires_at=NOW + timedelta(minutes=10),
            now=NOW,
            grant_id=GRANT_ID,
        )
        self.claimed_by: list[str] = []
        self.recorded_decisions: list[dict[str, Any]] = []
        self.completed: list[dict[str, Any]] = []
        self.idempotency_checks: list[str] = []

    def claim_next_execution_work_item(self, *, worker_id: str, now=None):
        self.claimed_by.append(worker_id)
        if self.work_item is None:
            return None
        claimed = replace(
            self.work_item,
            status="claimed",
            claimed_by=worker_id,
            claimed_at=now or NOW,
            attempt_count=self.work_item.attempt_count + 1,
            updated_at=now or NOW,
        )
        self.work_item = claimed
        return claimed

    def claim_execution_work_item(self, *, work_item_id: str, worker_id: str, now=None):
        if self.work_item is None or self.work_item.work_item_id != work_item_id:
            return None
        return self.claim_next_execution_work_item(worker_id=worker_id, now=now)

    def get_grant(self, grant_id: str):
        return self.grant if grant_id == self.grant.grant_id else None

    def get_batch_request(self, batch_request_id: str):
        return self.batch if batch_request_id == self.batch.batch_request_id else None

    def get_policy_ceiling(self, policy_id: str):
        if self.policy is None:
            return None
        return self.policy if policy_id == self.policy.policy_id else None

    def execution_decision_exists(self, idempotency_key: str) -> bool:
        self.idempotency_checks.append(idempotency_key)
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
        self.completed.append(
            {
                "work_item_id": work_item_id,
                "decision": decision.to_dict(),
                "status": "completed" if decision.status == "accepted" else "failed",
            }
        )
        return replace(
            self.work_item,
            status=self.completed[-1]["status"],
            decision=decision.to_dict(),
            completed_at=now or NOW,
            updated_at=now or NOW,
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
        max_orders=1,
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
        ),
        context_refs=({"type": "research_document", "id": "doc-1"},),
        risk_summary={"paper_only": True, "live_trading": "forbidden"},
    )


def _work_item(**overrides: Any) -> PaperExecutionWorkItem:
    values = {
        "work_item_id": WORK_ITEM_ID,
        "tenant_id": TENANT_ID,
        "batch_request_id": BATCH_ID,
        "grant_id": GRANT_ID,
        "order_id": f"{BATCH_ID}:0",
        "requested_by_actor_id": ANALYST_ID,
        "idempotency_key": "idem-worker-loop",
        "status": "queued",
        "payload": {
            "schema_version": "paper-execution-work-item/v1",
            "quote_price": 980,
            "quote_as_of": (NOW - timedelta(seconds=10)).isoformat(),
            "now": NOW.isoformat(),
            "available_cash": 100_000,
            "current_gross_notional": 0,
            "current_net_notional": 0,
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


def test_queue_processor_returns_no_work_without_mutation() -> None:
    store = _FakeQueueStore(work_item=None)
    processor = PaperExecutionQueueProcessor(
        store=store,
        worker_id="paper-worker-1",
        now=lambda: NOW,
    )

    result = processor.process_once()

    assert result.status == "no_work"
    assert result.work_item_id is None
    assert result.decision is None
    assert store.recorded_decisions == []
    assert store.completed == []


def test_queue_processor_executes_records_and_completes_accepted_work_item() -> None:
    store = _FakeQueueStore(work_item=_work_item())
    processor = PaperExecutionQueueProcessor(
        store=store,
        worker_id="paper-worker-1",
        now=lambda: NOW,
    )

    result = processor.process_once()

    assert result.status == "processed"
    assert result.work_item_id == WORK_ITEM_ID
    assert result.decision is not None
    assert result.decision.status == "accepted"
    assert store.claimed_by == ["paper-worker-1"]
    assert store.idempotency_checks == ["idem-worker-loop"]
    assert store.recorded_decisions[0]["decision"]["status"] == "accepted"
    assert store.completed[0]["status"] == "completed"
    assert store.completed[0]["decision"]["fill"]["mode"] == "paper"
    assert "fyers" not in str(result.decision.to_dict()).lower()


def test_queue_processor_fails_closed_when_policy_is_missing() -> None:
    store = _FakeQueueStore(work_item=_work_item())
    store.policy = None
    processor = PaperExecutionQueueProcessor(
        store=store,
        worker_id="paper-worker-1",
        now=lambda: NOW,
    )

    result = processor.process_once()

    assert result.status == "failed"
    assert result.decision is not None
    assert result.decision.status == "rejected"
    assert "policy_not_found" in result.decision.reasons
    assert store.recorded_decisions == []
    assert store.completed[0]["status"] == "failed"


def test_queue_processor_fails_closed_on_malformed_payload_without_recording() -> None:
    store = _FakeQueueStore(
        work_item=_work_item(payload={"schema_version": "paper-execution-work-item/v1"})
    )
    processor = PaperExecutionQueueProcessor(
        store=store,
        worker_id="paper-worker-1",
        now=lambda: NOW,
    )

    result = processor.process_once()

    assert result.status == "failed"
    assert result.decision is not None
    assert result.decision.status == "rejected"
    assert "invalid_work_item_payload" in result.decision.reasons
    assert store.recorded_decisions == []
    assert store.completed[0]["status"] == "failed"
