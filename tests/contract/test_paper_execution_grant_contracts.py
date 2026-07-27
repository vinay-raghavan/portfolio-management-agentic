from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from portfolio_domain import (
    PaperBatchRequest,
    PaperExecutionGrant,
    PaperExecutionOrder,
    PaperExecutionPolicyCeiling,
    evaluate_paper_execution_order,
    issue_paper_execution_grant,
)


NOW = datetime(2026, 7, 27, 9, 15, tzinfo=timezone.utc)


def _configured_policy() -> PaperExecutionPolicyCeiling:
    return PaperExecutionPolicyCeiling(
        policy_id="policy-1",
        tenant_id="tenant-a",
        created_by_actor_id="admin-1",
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


def _batch_request() -> PaperBatchRequest:
    return PaperBatchRequest(
        batch_request_id="batch-1",
        tenant_id="tenant-a",
        requested_by_actor_id="analyst-1",
        strategy_key="breakout-continuation",
        status="proposed",
        orders=(
            PaperExecutionOrder(
                symbol="TATAMOTORS",
                side="buy",
                quantity=5,
                order_type="market",
                limit_price=None,
            ),
        ),
        context_refs=({"type": "research_document", "id": "doc-1"},),
        risk_summary={"paper_only": True, "live_trading": "forbidden"},
    )


def test_policy_ceiling_without_required_fields_is_disabled_and_cannot_grant() -> None:
    policy = PaperExecutionPolicyCeiling.disabled(
        policy_id="policy-disabled",
        tenant_id="tenant-a",
        created_by_actor_id="admin-1",
        name="Incomplete policy",
    )
    batch = _batch_request()

    assert policy.status == "disabled"
    assert policy.configuration_complete is False
    assert policy.missing_required_fields == (
        "permitted_strategies",
        "permitted_symbols",
        "permitted_sides",
        "permitted_order_types",
        "max_orders",
        "max_quantity_per_order",
        "max_notional_per_order",
        "max_gross_notional",
        "max_net_notional",
        "max_loss_limit",
        "max_drawdown_limit",
        "slippage_bps",
        "quote_freshness_seconds",
        "valid_until",
    )
    with pytest.raises(ValueError, match="incomplete"):
        issue_paper_execution_grant(
            policy=policy,
            batch_request=batch,
            approved_by_actor_id="approver-1",
            expires_at=NOW + timedelta(minutes=10),
            now=NOW,
        )


def test_grant_is_bound_to_human_actor_and_no_broader_than_policy_or_request() -> None:
    policy = _configured_policy()
    batch = _batch_request()

    grant = issue_paper_execution_grant(
        policy=policy,
        batch_request=batch,
        approved_by_actor_id="approver-1",
        expires_at=NOW + timedelta(minutes=10),
        now=NOW,
    )

    assert isinstance(grant, PaperExecutionGrant)
    assert grant.status == "active"
    assert grant.approved_by_actor_id == "approver-1"
    assert grant.batch_request_id == batch.batch_request_id
    assert grant.policy_ceiling_id == policy.policy_id
    assert grant.scope == {
        "strategies": ("breakout-continuation",),
        "symbols": ("TATAMOTORS",),
        "sides": ("buy",),
        "order_types": ("market",),
        "max_orders": 1,
        "max_quantity_per_order": 5,
        "max_notional_per_order": 20_000,
        "max_gross_notional": 40_000,
        "max_net_notional": 40_000,
    }
    assert "access_token" not in str(grant.to_dict()).lower()
    assert "fyers" not in str(grant.to_dict()).lower()


def test_self_approval_is_rejected_unless_policy_explicitly_permits_it() -> None:
    with pytest.raises(ValueError, match="self-approval"):
        issue_paper_execution_grant(
            policy=_configured_policy(),
            batch_request=_batch_request(),
            approved_by_actor_id="analyst-1",
            expires_at=NOW + timedelta(minutes=10),
            now=NOW,
        )


def test_execution_rejects_revoked_expired_grant_stale_quote_duplicate_and_limits() -> None:
    policy = _configured_policy()
    batch = _batch_request()
    grant = issue_paper_execution_grant(
        policy=policy,
        batch_request=batch,
        approved_by_actor_id="approver-1",
        expires_at=NOW + timedelta(minutes=10),
        now=NOW,
    )
    order = batch.orders[0]
    revoked_grant = PaperExecutionGrant(
        grant_id=grant.grant_id,
        tenant_id=grant.tenant_id,
        batch_request_id=grant.batch_request_id,
        policy_ceiling_id=grant.policy_ceiling_id,
        approved_by_actor_id=grant.approved_by_actor_id,
        status="revoked",
        expires_at=grant.expires_at,
        scope=grant.scope,
        reserved_capacity=grant.reserved_capacity,
        consumed_capacity=grant.consumed_capacity,
    )

    revoked = evaluate_paper_execution_order(
        policy=policy,
        grant=revoked_grant,
        batch_request=batch,
        order=order,
        idempotency_key="idem-revoked",
        quote_price=980.0,
        quote_as_of=NOW,
        now=NOW,
    )
    expired = evaluate_paper_execution_order(
        policy=policy,
        grant=grant,
        batch_request=batch,
        order=order,
        idempotency_key="idem-expired",
        quote_price=980.0,
        quote_as_of=NOW,
        now=NOW + timedelta(minutes=11),
    )
    stale = evaluate_paper_execution_order(
        policy=policy,
        grant=grant,
        batch_request=batch,
        order=order,
        idempotency_key="idem-stale",
        quote_price=980.0,
        quote_as_of=NOW - timedelta(minutes=2),
        now=NOW,
    )
    duplicate = evaluate_paper_execution_order(
        policy=policy,
        grant=grant,
        batch_request=batch,
        order=order,
        idempotency_key="idem-seen",
        quote_price=980.0,
        quote_as_of=NOW,
        now=NOW,
        used_idempotency_keys={"idem-seen"},
    )
    oversize = evaluate_paper_execution_order(
        policy=policy,
        grant=grant,
        batch_request=batch,
        order=PaperExecutionOrder(
            symbol="TATAMOTORS",
            side="buy",
            quantity=50,
            order_type="market",
        ),
        idempotency_key="idem-oversize",
        quote_price=980.0,
        quote_as_of=NOW,
        now=NOW,
    )
    killed = evaluate_paper_execution_order(
        policy=policy,
        grant=grant,
        batch_request=batch,
        order=order,
        idempotency_key="idem-killed",
        quote_price=980.0,
        quote_as_of=NOW,
        now=NOW,
        kill_switch_active=True,
    )

    assert revoked.status == "rejected"
    assert "grant_revoked" in revoked.reasons
    assert expired.status == "rejected"
    assert "grant_expired" in expired.reasons
    assert stale.status == "rejected"
    assert "quote_stale" in stale.reasons
    assert duplicate.status == "rejected"
    assert "duplicate_idempotency_key" in duplicate.reasons
    assert oversize.status == "rejected"
    assert "quantity_limit_exceeded" in oversize.reasons
    assert killed.status == "rejected"
    assert "execution_kill_switch_active" in killed.reasons
    assert all(
        decision.fill is None
        for decision in (revoked, expired, stale, duplicate, oversize, killed)
    )


def test_execution_accepts_fresh_in_scope_paper_order_without_live_provider_fields() -> None:
    policy = _configured_policy()
    batch = _batch_request()
    grant = issue_paper_execution_grant(
        policy=policy,
        batch_request=batch,
        approved_by_actor_id="approver-1",
        expires_at=NOW + timedelta(minutes=10),
        now=NOW,
    )

    decision = evaluate_paper_execution_order(
        policy=policy,
        grant=grant,
        batch_request=batch,
        order=batch.orders[0],
        idempotency_key="idem-ok",
        quote_price=980.0,
        quote_as_of=NOW - timedelta(seconds=10),
        now=NOW,
        available_cash=100_000,
        current_gross_notional=5_000,
        current_net_notional=5_000,
    )

    assert decision.status == "accepted"
    assert decision.reasons == ()
    assert decision.fill == {
        "mode": "paper",
        "symbol": "TATAMOTORS",
        "side": "buy",
        "quantity": 5,
        "fill_price": 980.0,
        "notional": 4_900.0,
        "idempotency_key": "idem-ok",
        "grant_id": grant.grant_id,
    }
    payload = decision.to_dict()
    assert payload["audit_event"]["event_type"] == "paper_execution_accepted"
    assert "live" not in str(payload["fill"]).lower()
    assert "fyers" not in str(payload).lower()
    assert "token" not in str(payload).lower()
