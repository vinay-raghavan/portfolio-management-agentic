from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .paper_execution import (
    PaperBatchRequest,
    PaperExecutionDecision,
    PaperExecutionGrant,
    PaperExecutionOrder,
    PaperExecutionPolicyCeiling,
    issue_paper_execution_grant,
)


class PostgresPaperExecutionStore:
    """Tenant-scoped storage adapter for protected paper execution workflows."""

    def __init__(
        self,
        *,
        tenant_id: str,
        connection_factory: Callable[[], Any],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required for paper execution storage")
        self._tenant_id = tenant_id
        self._connection_factory = connection_factory
        self._now = now or _utc_now

    def upsert_policy_ceiling(
        self,
        policy: PaperExecutionPolicyCeiling,
    ) -> PaperExecutionPolicyCeiling:
        self._require_tenant(policy.tenant_id)
        current_time = _aware_utc(self._now())
        params = {
            "policy_id": policy.policy_id,
            "tenant_id": self._tenant_id,
            "created_by_actor_id": _blank_to_none(policy.created_by_actor_id),
            "name": policy.name,
            "status": policy.status,
            "valid_from": _optional_aware_utc(policy.valid_from),
            "valid_until": _optional_aware_utc(policy.valid_until),
            "permitted_strategies": list(policy.permitted_strategies),
            "permitted_symbols": list(policy.permitted_symbols),
            "permitted_universes": [],
            "permitted_sides": list(policy.permitted_sides),
            "permitted_order_types": list(policy.permitted_order_types),
            "limits": _policy_limits(policy),
            "freshness_requirements": {
                "quote_freshness_seconds": policy.quote_freshness_seconds
            },
            "self_approval_permitted": policy.self_approval_permitted,
            "now": current_time,
        }
        _reject_secret_payload(params)
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO paper_execution_policy_ceilings (
                        id,
                        tenant_id,
                        created_by_actor_id,
                        name,
                        status,
                        valid_from,
                        valid_until,
                        permitted_strategies,
                        permitted_symbols,
                        permitted_universes,
                        permitted_sides,
                        permitted_order_types,
                        limits,
                        freshness_requirements,
                        self_approval_permitted,
                        created_at,
                        updated_at
                    ) VALUES (
                        %(policy_id)s,
                        %(tenant_id)s,
                        %(created_by_actor_id)s,
                        %(name)s,
                        %(status)s,
                        %(valid_from)s,
                        %(valid_until)s,
                        %(permitted_strategies)s,
                        %(permitted_symbols)s,
                        %(permitted_universes)s,
                        %(permitted_sides)s,
                        %(permitted_order_types)s,
                        %(limits)s,
                        %(freshness_requirements)s,
                        %(self_approval_permitted)s,
                        %(now)s,
                        %(now)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        status = EXCLUDED.status,
                        valid_from = EXCLUDED.valid_from,
                        valid_until = EXCLUDED.valid_until,
                        permitted_strategies = EXCLUDED.permitted_strategies,
                        permitted_symbols = EXCLUDED.permitted_symbols,
                        permitted_universes = EXCLUDED.permitted_universes,
                        permitted_sides = EXCLUDED.permitted_sides,
                        permitted_order_types = EXCLUDED.permitted_order_types,
                        limits = EXCLUDED.limits,
                        freshness_requirements = EXCLUDED.freshness_requirements,
                        self_approval_permitted = EXCLUDED.self_approval_permitted,
                        updated_at = %(now)s
                    WHERE paper_execution_policy_ceilings.tenant_id = %(tenant_id)s
                    """.strip(),
                    params,
                )
            connection.commit()
        return policy

    def create_batch_request(
        self,
        batch_request: PaperBatchRequest,
    ) -> PaperBatchRequest:
        self._require_tenant(batch_request.tenant_id)
        current_time = _aware_utc(self._now())
        params = {
            "batch_request_id": batch_request.batch_request_id,
            "tenant_id": self._tenant_id,
            "requested_by_actor_id": _blank_to_none(
                batch_request.requested_by_actor_id
            ),
            "strategy_key": batch_request.strategy_key,
            "status": batch_request.status,
            "orders": [order.to_dict() for order in batch_request.orders],
            "context_refs": [dict(ref) for ref in batch_request.context_refs],
            "risk_summary": dict(batch_request.risk_summary),
            "now": current_time,
        }
        _reject_secret_payload(params)
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO paper_batch_requests (
                        id,
                        tenant_id,
                        requested_by_actor_id,
                        strategy_key,
                        status,
                        orders,
                        context_refs,
                        risk_summary,
                        created_at,
                        updated_at
                    ) VALUES (
                        %(batch_request_id)s,
                        %(tenant_id)s,
                        %(requested_by_actor_id)s,
                        %(strategy_key)s,
                        %(status)s,
                        %(orders)s,
                        %(context_refs)s,
                        %(risk_summary)s,
                        %(now)s,
                        %(now)s
                    )
                    """.strip(),
                    params,
                )
            connection.commit()
        return batch_request

    def issue_grant(
        self,
        *,
        policy: PaperExecutionPolicyCeiling,
        batch_request: PaperBatchRequest,
        approved_by_actor_id: str,
        expires_at: datetime,
    ) -> PaperExecutionGrant:
        self._require_tenant(policy.tenant_id)
        self._require_tenant(batch_request.tenant_id)
        grant = issue_paper_execution_grant(
            policy=policy,
            batch_request=batch_request,
            approved_by_actor_id=approved_by_actor_id,
            expires_at=expires_at,
            now=self._now(),
            grant_id=str(uuid4()),
        )
        params = {
            "grant_id": grant.grant_id,
            "tenant_id": self._tenant_id,
            "batch_request_id": grant.batch_request_id,
            "policy_ceiling_id": grant.policy_ceiling_id,
            "approved_by_actor_id": grant.approved_by_actor_id,
            "status": grant.status,
            "expires_at": _aware_utc(grant.expires_at),
            "scope": _json_safe(grant.scope),
            "reserved_capacity": _json_safe(grant.reserved_capacity),
            "consumed_capacity": _json_safe(grant.consumed_capacity),
            "now": _aware_utc(self._now()),
        }
        _reject_secret_payload(params)
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO paper_execution_grants (
                        id,
                        tenant_id,
                        batch_request_id,
                        policy_ceiling_id,
                        approved_by_actor_id,
                        status,
                        expires_at,
                        scope,
                        reserved_capacity,
                        consumed_capacity,
                        created_at,
                        updated_at
                    ) VALUES (
                        %(grant_id)s,
                        %(tenant_id)s,
                        %(batch_request_id)s,
                        %(policy_ceiling_id)s,
                        %(approved_by_actor_id)s,
                        %(status)s,
                        %(expires_at)s,
                        %(scope)s,
                        %(reserved_capacity)s,
                        %(consumed_capacity)s,
                        %(now)s,
                        %(now)s
                    )
                    """.strip(),
                    params,
                )
            connection.commit()
        return grant

    def record_execution_decision(
        self,
        *,
        grant: PaperExecutionGrant,
        batch_request: PaperBatchRequest,
        order: PaperExecutionOrder,
        decision: PaperExecutionDecision,
        fill_price: float,
        exposure_after: Mapping[str, Any],
    ) -> PaperExecutionDecision:
        self._require_tenant(grant.tenant_id)
        self._require_tenant(batch_request.tenant_id)
        decision_payload = decision.to_dict()
        fill_payload = decision_payload["fill"]
        idempotency_key = str(decision.audit_event.get("idempotency_key", "")).strip()
        if not idempotency_key:
            raise ValueError("paper execution decision requires an idempotency key")
        params = {
            "tenant_id": self._tenant_id,
            "grant_id": grant.grant_id,
            "batch_request_id": batch_request.batch_request_id,
            "idempotency_key": idempotency_key,
            "entry_type": "paper_execution_decision",
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "price": fill_price,
            "notional": decision.audit_event.get("notional", 0.0),
            "status": decision.status,
            "decision": _json_safe(decision_payload),
            "fill": _json_safe(fill_payload) if fill_payload is not None else None,
            "exposure_after": _json_safe(exposure_after),
            "now": _aware_utc(self._now()),
        }
        _reject_secret_payload(params)
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO paper_ledger_entries (
                        tenant_id,
                        grant_id,
                        batch_request_id,
                        idempotency_key,
                        entry_type,
                        symbol,
                        side,
                        quantity,
                        price,
                        notional,
                        status,
                        decision,
                        fill,
                        exposure_after,
                        created_at
                    ) VALUES (
                        %(tenant_id)s,
                        %(grant_id)s,
                        %(batch_request_id)s,
                        %(idempotency_key)s,
                        %(entry_type)s,
                        %(symbol)s,
                        %(side)s,
                        %(quantity)s,
                        %(price)s,
                        %(notional)s,
                        %(status)s,
                        %(decision)s,
                        %(fill)s,
                        %(exposure_after)s,
                        %(now)s
                    )
                    ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
                    """.strip(),
                    params,
                )
            connection.commit()
        return decision

    def _require_tenant(self, tenant_id: str) -> None:
        if tenant_id != self._tenant_id:
            raise ValueError("Paper execution storage tenant mismatch")


def _policy_limits(policy: PaperExecutionPolicyCeiling) -> dict[str, Any]:
    return {
        "max_orders": policy.max_orders,
        "max_quantity_per_order": policy.max_quantity_per_order,
        "max_notional_per_order": policy.max_notional_per_order,
        "max_gross_notional": policy.max_gross_notional,
        "max_net_notional": policy.max_net_notional,
        "max_loss_limit": policy.max_loss_limit,
        "max_drawdown_limit": policy.max_drawdown_limit,
        "slippage_bps": policy.slippage_bps,
        "market_hours_only": policy.market_hours_only,
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return _aware_utc(value).isoformat()
    return value


def _reject_secret_payload(payload: Mapping[str, Any]) -> None:
    lowered = str(payload).lower()
    forbidden = (
        "access_token",
        "refresh_token",
        "api_key",
        "authorization:",
        "bearer ",
        "password",
        "secret",
        "fyers",
        "trading_token",
    )
    if any(fragment in lowered for fragment in forbidden):
        raise ValueError("Paper execution payload may not contain secrets")


def _blank_to_none(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _optional_aware_utc(value: datetime | None) -> datetime | None:
    return _aware_utc(value) if value is not None else None


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
