from __future__ import annotations

import json
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

    def get_policy_ceiling(
        self,
        policy_id: str,
    ) -> PaperExecutionPolicyCeiling | None:
        policy_id = policy_id.strip()
        if not policy_id:
            raise ValueError("policy_id is required")
        params = {"tenant_id": self._tenant_id, "policy_id": policy_id}
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        tenant_id,
                        created_by_actor_id,
                        name,
                        status,
                        valid_from,
                        valid_until,
                        permitted_strategies,
                        permitted_symbols,
                        permitted_sides,
                        permitted_order_types,
                        limits,
                        freshness_requirements,
                        self_approval_permitted
                    FROM paper_execution_policy_ceilings
                    WHERE tenant_id = %(tenant_id)s
                      AND id = %(policy_id)s
                    """.strip(),
                    params,
                )
                row = _fetch_one_mapping(cursor)
        if row is None:
            return None
        policy = _policy_from_row(row)
        self._require_tenant(policy.tenant_id)
        _reject_secret_payload(policy.to_dict())
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

    def get_batch_request(
        self,
        batch_request_id: str,
    ) -> PaperBatchRequest | None:
        batch_request_id = batch_request_id.strip()
        if not batch_request_id:
            raise ValueError("batch_request_id is required")
        params = {"tenant_id": self._tenant_id, "batch_request_id": batch_request_id}
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        tenant_id,
                        requested_by_actor_id,
                        strategy_key,
                        status,
                        orders,
                        context_refs,
                        risk_summary
                    FROM paper_batch_requests
                    WHERE tenant_id = %(tenant_id)s
                      AND id = %(batch_request_id)s
                    """.strip(),
                    params,
                )
                row = _fetch_one_mapping(cursor)
        if row is None:
            return None
        batch_request = _batch_from_row(row)
        self._require_tenant(batch_request.tenant_id)
        _reject_secret_payload(batch_request.to_dict())
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

    def get_grant(
        self,
        grant_id: str,
    ) -> PaperExecutionGrant | None:
        grant_id = grant_id.strip()
        if not grant_id:
            raise ValueError("grant_id is required")
        params = {"tenant_id": self._tenant_id, "grant_id": grant_id}
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        tenant_id,
                        batch_request_id,
                        policy_ceiling_id,
                        approved_by_actor_id,
                        status,
                        expires_at,
                        scope,
                        reserved_capacity,
                        consumed_capacity
                    FROM paper_execution_grants
                    WHERE tenant_id = %(tenant_id)s
                      AND id = %(grant_id)s
                    """.strip(),
                    params,
                )
                row = _fetch_one_mapping(cursor)
        if row is None:
            return None
        grant = _grant_from_row(row)
        self._require_tenant(grant.tenant_id)
        _reject_secret_payload(grant.to_dict())
        return grant

    def revoke_grant(
        self,
        grant_id: str,
    ) -> PaperExecutionGrant | None:
        grant_id = grant_id.strip()
        if not grant_id:
            raise ValueError("grant_id is required")
        params = {
            "tenant_id": self._tenant_id,
            "grant_id": grant_id,
            "now": _aware_utc(self._now()),
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE paper_execution_grants
                    SET
                        status = 'revoked',
                        revoked_at = %(now)s,
                        updated_at = %(now)s
                    WHERE tenant_id = %(tenant_id)s
                      AND id = %(grant_id)s
                      AND status = 'active'
                    RETURNING
                        id,
                        tenant_id,
                        batch_request_id,
                        policy_ceiling_id,
                        approved_by_actor_id,
                        status,
                        expires_at,
                        scope,
                        reserved_capacity,
                        consumed_capacity
                    """.strip(),
                    params,
                )
                row = _fetch_one_mapping(cursor)
            connection.commit()
        if row is None:
            return None
        grant = _grant_from_row(row)
        self._require_tenant(grant.tenant_id)
        _reject_secret_payload(grant.to_dict())
        return grant

    def execution_decision_exists(self, idempotency_key: str) -> bool:
        clean_key = idempotency_key.strip()
        if not clean_key:
            return False
        params = {
            "tenant_id": self._tenant_id,
            "idempotency_key": clean_key,
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT TRUE AS exists
                    FROM paper_ledger_entries
                    WHERE tenant_id = %(tenant_id)s
                      AND idempotency_key = %(idempotency_key)s
                    LIMIT 1
                    """.strip(),
                    params,
                )
                row = _fetch_one_mapping(cursor)
        return bool(row and row.get("exists"))

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
                    RETURNING id
                    """.strip(),
                    params,
                )
                row = _fetch_one_mapping(cursor)
                if row is not None and decision.status == "accepted":
                    cursor.execute(
                        """
                        UPDATE paper_execution_grants
                        SET
                            consumed_capacity = jsonb_build_object(
                                'order_count',
                                COALESCE((consumed_capacity->>'order_count')::numeric, 0)
                                    + %(order_count_delta)s,
                                'gross_notional',
                                COALESCE((consumed_capacity->>'gross_notional')::numeric, 0)
                                    + %(gross_notional_delta)s,
                                'net_notional',
                                COALESCE((consumed_capacity->>'net_notional')::numeric, 0)
                                    + %(net_notional_delta)s
                            ),
                            updated_at = %(now)s
                        WHERE tenant_id = %(tenant_id)s
                          AND id = %(grant_id)s
                          AND status = 'active'
                        """.strip(),
                        {
                            **params,
                            **_grant_capacity_delta(order, decision),
                        },
                    )
            connection.commit()
        if row is None:
            return _duplicate_idempotency_decision(decision)
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


def _duplicate_idempotency_decision(
    decision: PaperExecutionDecision,
) -> PaperExecutionDecision:
    audit_event = dict(decision.audit_event)
    audit_event["event_type"] = "paper_execution_rejected"
    audit_event["reasons"] = ("duplicate_idempotency_key",)
    return PaperExecutionDecision(
        status="rejected",
        reasons=("duplicate_idempotency_key",),
        fill=None,
        audit_event=audit_event,
    )


def _grant_capacity_delta(
    order: PaperExecutionOrder,
    decision: PaperExecutionDecision,
) -> dict[str, float | int]:
    notional = float(decision.audit_event.get("notional", 0.0))
    net_notional = notional if order.side == "buy" else -notional
    return {
        "order_count_delta": 1,
        "gross_notional_delta": abs(notional),
        "net_notional_delta": net_notional,
    }


def _fetch_one_mapping(cursor: Any) -> dict[str, Any] | None:
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, Mapping):
        return {str(key): value for key, value in row.items()}
    columns = [str(column[0]) for column in cursor.description]
    return dict(zip(columns, row, strict=False))


def _policy_from_row(row: Mapping[str, Any]) -> PaperExecutionPolicyCeiling:
    limits = _mapping_value(row.get("limits"))
    freshness_requirements = _mapping_value(row.get("freshness_requirements"))
    return PaperExecutionPolicyCeiling(
        policy_id=str(row.get("id", "")),
        tenant_id=str(row.get("tenant_id", "")),
        created_by_actor_id=str(row.get("created_by_actor_id") or ""),
        name=str(row.get("name", "")),
        status=str(row.get("status", "")),
        permitted_strategies=tuple(_list_value(row.get("permitted_strategies"))),
        permitted_symbols=tuple(_list_value(row.get("permitted_symbols"))),
        permitted_sides=tuple(_list_value(row.get("permitted_sides"))),
        permitted_order_types=tuple(_list_value(row.get("permitted_order_types"))),
        max_orders=_optional_int(limits.get("max_orders")),
        max_quantity_per_order=_optional_int(limits.get("max_quantity_per_order")),
        max_notional_per_order=_optional_float(limits.get("max_notional_per_order")),
        max_gross_notional=_optional_float(limits.get("max_gross_notional")),
        max_net_notional=_optional_float(limits.get("max_net_notional")),
        max_loss_limit=_optional_float(limits.get("max_loss_limit")),
        max_drawdown_limit=_optional_float(limits.get("max_drawdown_limit")),
        slippage_bps=_optional_int(limits.get("slippage_bps")),
        quote_freshness_seconds=_optional_int(
            freshness_requirements.get("quote_freshness_seconds")
        ),
        market_hours_only=bool(limits.get("market_hours_only", True)),
        self_approval_permitted=bool(row.get("self_approval_permitted", False)),
        valid_from=_optional_datetime(row.get("valid_from")),
        valid_until=_optional_datetime(row.get("valid_until")),
    )


def _batch_from_row(row: Mapping[str, Any]) -> PaperBatchRequest:
    orders = tuple(_order_from_payload(order) for order in _list_value(row.get("orders")))
    return PaperBatchRequest(
        batch_request_id=str(row.get("id", "")),
        tenant_id=str(row.get("tenant_id", "")),
        requested_by_actor_id=str(row.get("requested_by_actor_id") or ""),
        strategy_key=str(row.get("strategy_key", "")),
        status=str(row.get("status", "")),
        orders=orders,
        context_refs=tuple(_mapping_value(ref) for ref in _list_value(row.get("context_refs"))),
        risk_summary=_mapping_value(row.get("risk_summary")),
    )


def _order_from_payload(payload: Any) -> PaperExecutionOrder:
    order = _mapping_value(payload)
    return PaperExecutionOrder(
        symbol=str(order.get("symbol", "")),
        side=str(order.get("side", "")),
        quantity=int(order.get("quantity", 0)),
        order_type=str(order.get("order_type", "")),
        limit_price=_optional_float(order.get("limit_price")),
    )


def _grant_from_row(row: Mapping[str, Any]) -> PaperExecutionGrant:
    return PaperExecutionGrant(
        grant_id=str(row.get("id", "")),
        tenant_id=str(row.get("tenant_id", "")),
        batch_request_id=str(row.get("batch_request_id", "")),
        policy_ceiling_id=str(row.get("policy_ceiling_id", "")),
        approved_by_actor_id=str(row.get("approved_by_actor_id") or ""),
        status=str(row.get("status", "")),
        expires_at=_required_datetime(row.get("expires_at")),
        scope=_mapping_value(row.get("scope")),
        reserved_capacity=_mapping_value(row.get("reserved_capacity")),
        consumed_capacity=_mapping_value(row.get("consumed_capacity")),
    )


def _mapping_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, Mapping):
        raise ValueError("Expected mapping payload from paper execution store")
    return {str(key): _json_safe(item) for key, item in value.items()}


def _list_value(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        value = json.loads(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return value
    raise ValueError("Expected list payload from paper execution store")


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _required_datetime(value: Any) -> datetime:
    parsed = _optional_datetime(value)
    if parsed is None:
        raise ValueError("Expected datetime payload from paper execution store")
    return parsed


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _aware_utc(value)
    if isinstance(value, str):
        return _aware_utc(datetime.fromisoformat(value))
    raise ValueError("Expected datetime payload from paper execution store")


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
