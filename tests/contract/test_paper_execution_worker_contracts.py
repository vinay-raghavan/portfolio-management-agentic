from __future__ import annotations

from datetime import datetime, timedelta, timezone

from portfolio_domain import (
    DeterministicPaperExecutionWorker,
    PaperBatchRequest,
    PaperExecutionDecision,
    PaperExecutionOrder,
    PaperExecutionPolicyCeiling,
    PaperExecutionWorkerRequest,
    issue_paper_execution_grant,
)


NOW = datetime(2026, 7, 27, 9, 15, tzinfo=timezone.utc)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
ADMIN_ID = "22222222-2222-2222-2222-222222222222"
ANALYST_ID = "33333333-3333-3333-3333-333333333333"
APPROVER_ID = "44444444-4444-4444-4444-444444444444"
POLICY_ID = "55555555-5555-5555-5555-555555555555"
BATCH_ID = "66666666-6666-6666-6666-666666666666"


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


def _request(
    *,
    idempotency_key: str = "idem-worker-ok",
    used_idempotency_keys: set[str] | None = None,
) -> PaperExecutionWorkerRequest:
    policy = _policy()
    batch = _batch()
    grant = issue_paper_execution_grant(
        policy=policy,
        batch_request=batch,
        approved_by_actor_id=APPROVER_ID,
        expires_at=NOW + timedelta(minutes=10),
        now=NOW,
        grant_id="77777777-7777-7777-7777-777777777777",
    )
    order = batch.orders[0]
    return PaperExecutionWorkerRequest(
        policy=policy,
        grant=grant,
        batch_request=batch,
        order=order,
        idempotency_key=idempotency_key,
        quote_price=980,
        quote_as_of=NOW - timedelta(seconds=10),
        now=NOW,
        used_idempotency_keys=used_idempotency_keys or set(),
        available_cash=100_000,
        current_gross_notional=0,
        current_net_notional=0,
        kill_switch_active=False,
        exposure_after={"gross_notional": 4_900.0, "net_notional": 4_900.0},
    )


def test_worker_records_accepted_decision_and_returns_recorder_result() -> None:
    recorded: list[tuple[PaperExecutionDecision, PaperExecutionWorkerRequest]] = []

    def recorder(
        decision: PaperExecutionDecision,
        request: PaperExecutionWorkerRequest,
    ) -> PaperExecutionDecision:
        recorded.append((decision, request))
        return decision

    worker = DeterministicPaperExecutionWorker(record_decision=recorder)

    decision = worker.execute(_request())

    assert decision.status == "accepted"
    assert len(recorded) == 1
    recorded_decision, recorded_request = recorded[0]
    assert recorded_decision.fill is not None
    assert recorded_decision.fill["mode"] == "paper"
    assert recorded_request.exposure_after == {
        "gross_notional": 4_900.0,
        "net_notional": 4_900.0,
    }
    assert "fyers" not in str(recorded_decision.to_dict()).lower()


def test_worker_does_not_record_rejected_decision() -> None:
    recorded: list[PaperExecutionDecision] = []
    worker = DeterministicPaperExecutionWorker(
        record_decision=lambda decision, _request: recorded.append(decision)
        or decision
    )

    decision = worker.execute(
        _request(
            idempotency_key="idem-duplicate",
            used_idempotency_keys={"idem-duplicate"},
        )
    )

    assert decision.status == "rejected"
    assert "duplicate_idempotency_key" in decision.reasons
    assert recorded == []
