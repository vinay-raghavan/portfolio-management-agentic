from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timezone
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class PaperExecutionOrder:
    symbol: str
    side: str
    quantity: int
    order_type: str
    limit_price: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        object.__setattr__(self, "side", self.side.strip().lower())
        object.__setattr__(self, "order_type", self.order_type.strip().lower())
        if not self.symbol:
            raise ValueError("Paper execution symbol is required")
        if self.side not in {"buy", "sell"}:
            raise ValueError("Paper execution side must be buy or sell")
        if self.order_type not in {"market", "limit"}:
            raise ValueError("Paper execution order_type must be market or limit")
        if self.quantity <= 0:
            raise ValueError("Paper execution quantity must be positive")
        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("Paper execution limit_price must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperExecutionPolicyCeiling:
    policy_id: str
    tenant_id: str
    created_by_actor_id: str
    name: str
    status: str
    permitted_strategies: tuple[str, ...]
    permitted_symbols: tuple[str, ...]
    permitted_sides: tuple[str, ...]
    permitted_order_types: tuple[str, ...]
    max_orders: int | None
    max_quantity_per_order: int | None
    max_notional_per_order: float | None
    max_gross_notional: float | None
    max_net_notional: float | None
    max_loss_limit: float | None
    max_drawdown_limit: float | None
    slippage_bps: int | None
    quote_freshness_seconds: int | None
    market_hours_only: bool
    self_approval_permitted: bool
    valid_from: datetime | None
    valid_until: datetime | None

    @classmethod
    def disabled(
        cls,
        *,
        policy_id: str,
        tenant_id: str,
        created_by_actor_id: str,
        name: str,
    ) -> PaperExecutionPolicyCeiling:
        return cls(
            policy_id=policy_id,
            tenant_id=tenant_id,
            created_by_actor_id=created_by_actor_id,
            name=name,
            status="disabled",
            permitted_strategies=(),
            permitted_symbols=(),
            permitted_sides=(),
            permitted_order_types=(),
            max_orders=None,
            max_quantity_per_order=None,
            max_notional_per_order=None,
            max_gross_notional=None,
            max_net_notional=None,
            max_loss_limit=None,
            max_drawdown_limit=None,
            slippage_bps=None,
            quote_freshness_seconds=None,
            market_hours_only=True,
            self_approval_permitted=False,
            valid_from=None,
            valid_until=None,
        )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "permitted_strategies",
            tuple(_clean_lower_values(self.permitted_strategies)),
        )
        object.__setattr__(
            self,
            "permitted_symbols",
            tuple(_clean_upper_values(self.permitted_symbols)),
        )
        object.__setattr__(
            self,
            "permitted_sides",
            tuple(_clean_lower_values(self.permitted_sides)),
        )
        object.__setattr__(
            self,
            "permitted_order_types",
            tuple(_clean_lower_values(self.permitted_order_types)),
        )

    @property
    def missing_required_fields(self) -> tuple[str, ...]:
        missing: list[str] = []
        required_sequences = (
            ("permitted_strategies", self.permitted_strategies),
            ("permitted_symbols", self.permitted_symbols),
            ("permitted_sides", self.permitted_sides),
            ("permitted_order_types", self.permitted_order_types),
        )
        for name, value in required_sequences:
            if not value:
                missing.append(name)
        required_numbers = (
            ("max_orders", self.max_orders),
            ("max_quantity_per_order", self.max_quantity_per_order),
            ("max_notional_per_order", self.max_notional_per_order),
            ("max_gross_notional", self.max_gross_notional),
            ("max_net_notional", self.max_net_notional),
            ("max_loss_limit", self.max_loss_limit),
            ("max_drawdown_limit", self.max_drawdown_limit),
            ("slippage_bps", self.slippage_bps),
            ("quote_freshness_seconds", self.quote_freshness_seconds),
        )
        for name, value in required_numbers:
            if value is None or value <= 0:
                missing.append(name)
        if self.valid_until is None:
            missing.append("valid_until")
        return tuple(missing)

    @property
    def configuration_complete(self) -> bool:
        return not self.missing_required_fields

    def active_at(self, now: datetime) -> bool:
        current = _aware_utc(now)
        valid_from = _optional_aware_utc(self.valid_from)
        valid_until = _optional_aware_utc(self.valid_until)
        return (
            self.status == "enabled"
            and self.configuration_complete
            and (valid_from is None or valid_from <= current)
            and valid_until is not None
            and current < valid_until
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["valid_from"] = self.valid_from.isoformat() if self.valid_from else None
        payload["valid_until"] = self.valid_until.isoformat() if self.valid_until else None
        payload["configuration_complete"] = self.configuration_complete
        payload["missing_required_fields"] = self.missing_required_fields
        return payload


@dataclass(frozen=True)
class PaperBatchRequest:
    batch_request_id: str
    tenant_id: str
    requested_by_actor_id: str
    strategy_key: str
    status: str
    orders: tuple[PaperExecutionOrder, ...]
    context_refs: tuple[Mapping[str, Any], ...]
    risk_summary: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_key", self.strategy_key.strip().lower())
        object.__setattr__(self, "orders", tuple(self.orders))
        object.__setattr__(self, "context_refs", tuple(dict(ref) for ref in self.context_refs))
        object.__setattr__(self, "risk_summary", dict(self.risk_summary))
        if not self.batch_request_id.strip():
            raise ValueError("batch_request_id is required")
        if not self.tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not self.requested_by_actor_id.strip():
            raise ValueError("requested_by_actor_id is required")
        if not self.strategy_key:
            raise ValueError("strategy_key is required")
        if not self.orders:
            raise ValueError("Paper batch request requires at least one order")

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_request_id": self.batch_request_id,
            "tenant_id": self.tenant_id,
            "requested_by_actor_id": self.requested_by_actor_id,
            "strategy_key": self.strategy_key,
            "status": self.status,
            "orders": [order.to_dict() for order in self.orders],
            "context_refs": [dict(ref) for ref in self.context_refs],
            "risk_summary": dict(self.risk_summary),
        }


@dataclass(frozen=True)
class PaperExecutionGrant:
    grant_id: str
    tenant_id: str
    batch_request_id: str
    policy_ceiling_id: str
    approved_by_actor_id: str
    status: str
    expires_at: datetime
    scope: Mapping[str, Any]
    reserved_capacity: Mapping[str, Any]
    consumed_capacity: Mapping[str, Any]

    def active_at(self, now: datetime) -> bool:
        return self.status == "active" and _aware_utc(now) < _aware_utc(self.expires_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "tenant_id": self.tenant_id,
            "batch_request_id": self.batch_request_id,
            "policy_ceiling_id": self.policy_ceiling_id,
            "approved_by_actor_id": self.approved_by_actor_id,
            "status": self.status,
            "expires_at": self.expires_at.isoformat(),
            "scope": _safe_mapping(self.scope),
            "reserved_capacity": _safe_mapping(self.reserved_capacity),
            "consumed_capacity": _safe_mapping(self.consumed_capacity),
        }


@dataclass(frozen=True)
class PaperExecutionDecision:
    status: str
    reasons: tuple[str, ...]
    fill: Mapping[str, Any] | None
    audit_event: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reasons": self.reasons,
            "fill": dict(self.fill) if self.fill is not None else None,
            "audit_event": dict(self.audit_event),
        }


def issue_paper_execution_grant(
    *,
    policy: PaperExecutionPolicyCeiling,
    batch_request: PaperBatchRequest,
    approved_by_actor_id: str,
    expires_at: datetime,
    now: datetime,
) -> PaperExecutionGrant:
    if policy.tenant_id != batch_request.tenant_id:
        raise ValueError("Policy and batch request tenant mismatch")
    if policy.missing_required_fields:
        raise ValueError("Paper execution policy is incomplete")
    if not policy.active_at(now):
        raise ValueError("Paper execution policy is not active")
    if batch_request.status != "proposed":
        raise ValueError("Paper batch request must be proposed before grant issuance")
    approver = approved_by_actor_id.strip()
    if not approver:
        raise ValueError("approved_by_actor_id is required")
    if (
        approver == batch_request.requested_by_actor_id
        and not policy.self_approval_permitted
    ):
        raise ValueError("Paper execution self-approval is not permitted")
    if _aware_utc(expires_at) <= _aware_utc(now):
        raise ValueError("Paper execution grant must expire in the future")
    if policy.valid_until is not None and _aware_utc(expires_at) > _aware_utc(policy.valid_until):
        raise ValueError("Paper execution grant cannot outlive policy ceiling")

    _validate_batch_within_policy(policy, batch_request)
    scope = _grant_scope(policy, batch_request)
    return PaperExecutionGrant(
        grant_id=f"grant-{batch_request.batch_request_id}-{policy.policy_id}",
        tenant_id=batch_request.tenant_id,
        batch_request_id=batch_request.batch_request_id,
        policy_ceiling_id=policy.policy_id,
        approved_by_actor_id=approver,
        status="active",
        expires_at=_aware_utc(expires_at),
        scope=scope,
        reserved_capacity={
            "order_count": len(batch_request.orders),
            "max_quantity_per_order": scope["max_quantity_per_order"],
            "max_gross_notional": scope["max_gross_notional"],
            "max_net_notional": scope["max_net_notional"],
        },
        consumed_capacity={"order_count": 0, "gross_notional": 0.0, "net_notional": 0.0},
    )


def evaluate_paper_execution_order(
    *,
    policy: PaperExecutionPolicyCeiling,
    grant: PaperExecutionGrant,
    batch_request: PaperBatchRequest,
    order: PaperExecutionOrder,
    idempotency_key: str,
    quote_price: float,
    quote_as_of: datetime,
    now: datetime,
    used_idempotency_keys: Iterable[str] = (),
    available_cash: float | None = None,
    current_gross_notional: float = 0.0,
    current_net_notional: float = 0.0,
    kill_switch_active: bool = False,
) -> PaperExecutionDecision:
    current = _aware_utc(now)
    quote_time = _aware_utc(quote_as_of)
    reasons: list[str] = []
    clean_idempotency_key = idempotency_key.strip()
    notional = round(order.quantity * quote_price, 2) if quote_price > 0 else 0.0

    if kill_switch_active:
        reasons.append("execution_kill_switch_active")
    if not clean_idempotency_key:
        reasons.append("idempotency_key_required")
    if clean_idempotency_key in set(used_idempotency_keys):
        reasons.append("duplicate_idempotency_key")
    if grant.tenant_id != batch_request.tenant_id or policy.tenant_id != batch_request.tenant_id:
        reasons.append("tenant_mismatch")
    if grant.batch_request_id != batch_request.batch_request_id:
        reasons.append("grant_batch_mismatch")
    if grant.policy_ceiling_id != policy.policy_id:
        reasons.append("grant_policy_mismatch")
    if grant.status == "revoked":
        reasons.append("grant_revoked")
    elif not grant.active_at(current):
        reasons.append(
            "grant_expired"
            if _aware_utc(grant.expires_at) <= current
            else "grant_not_active"
        )
    if not policy.active_at(current):
        reasons.append("policy_not_active")
    if quote_price <= 0:
        reasons.append("quote_price_invalid")
    if (
        policy.quote_freshness_seconds is not None
        and (current - quote_time).total_seconds() > policy.quote_freshness_seconds
    ):
        reasons.append("quote_stale")
    if policy.market_hours_only and not _within_market_hours(current):
        reasons.append("outside_market_hours")
    _append_scope_reasons(reasons, policy, grant, batch_request, order)
    if policy.max_quantity_per_order is not None and order.quantity > policy.max_quantity_per_order:
        reasons.append("quantity_limit_exceeded")
    if policy.max_notional_per_order is not None and notional > policy.max_notional_per_order:
        reasons.append("notional_limit_exceeded")
    if policy.max_gross_notional is not None and current_gross_notional + notional > policy.max_gross_notional:
        reasons.append("gross_notional_limit_exceeded")
    net_after_order = (
        current_net_notional + notional
        if order.side == "buy"
        else current_net_notional - notional
    )
    if policy.max_net_notional is not None and abs(net_after_order) > policy.max_net_notional:
        reasons.append("net_notional_limit_exceeded")
    if order.side == "buy" and available_cash is not None and notional > available_cash:
        reasons.append("insufficient_paper_cash")

    if reasons:
        return _decision(
            status="rejected",
            reasons=tuple(dict.fromkeys(reasons)),
            fill=None,
            idempotency_key=clean_idempotency_key,
            grant_id=grant.grant_id,
            order=order,
            notional=notional,
            now=current,
        )

    fill = {
        "mode": "paper",
        "symbol": order.symbol,
        "side": order.side,
        "quantity": order.quantity,
        "fill_price": round(quote_price, 2),
        "notional": notional,
        "idempotency_key": clean_idempotency_key,
        "grant_id": grant.grant_id,
    }
    return _decision(
        status="accepted",
        reasons=(),
        fill=fill,
        idempotency_key=clean_idempotency_key,
        grant_id=grant.grant_id,
        order=order,
        notional=notional,
        now=current,
    )


def _decision(
    *,
    status: str,
    reasons: tuple[str, ...],
    fill: Mapping[str, Any] | None,
    idempotency_key: str,
    grant_id: str,
    order: PaperExecutionOrder,
    notional: float,
    now: datetime,
) -> PaperExecutionDecision:
    return PaperExecutionDecision(
        status=status,
        reasons=reasons,
        fill=fill,
        audit_event={
            "event_type": f"paper_execution_{status}",
            "actor": "deterministic_paper_executor",
            "created_at": now.isoformat(),
            "grant_id": grant_id,
            "idempotency_key": idempotency_key,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "notional": notional,
            "mode": "paper",
            "reasons": reasons,
        },
    )


def _validate_batch_within_policy(
    policy: PaperExecutionPolicyCeiling,
    batch_request: PaperBatchRequest,
) -> None:
    if batch_request.strategy_key not in policy.permitted_strategies:
        raise ValueError("Paper batch strategy is outside the policy ceiling")
    if policy.max_orders is not None and len(batch_request.orders) > policy.max_orders:
        raise ValueError("Paper batch order count exceeds policy ceiling")
    for order in batch_request.orders:
        if order.symbol not in policy.permitted_symbols:
            raise ValueError("Paper batch symbol is outside the policy ceiling")
        if order.side not in policy.permitted_sides:
            raise ValueError("Paper batch side is outside the policy ceiling")
        if order.order_type not in policy.permitted_order_types:
            raise ValueError("Paper batch order_type is outside the policy ceiling")
        if policy.max_quantity_per_order is not None and order.quantity > policy.max_quantity_per_order:
            raise ValueError("Paper batch quantity exceeds policy ceiling")


def _grant_scope(
    policy: PaperExecutionPolicyCeiling,
    batch_request: PaperBatchRequest,
) -> dict[str, Any]:
    symbols = tuple(dict.fromkeys(order.symbol for order in batch_request.orders))
    sides = tuple(dict.fromkeys(order.side for order in batch_request.orders))
    order_types = tuple(dict.fromkeys(order.order_type for order in batch_request.orders))
    max_quantity = max(order.quantity for order in batch_request.orders)
    return {
        "strategies": (batch_request.strategy_key,),
        "symbols": symbols,
        "sides": sides,
        "order_types": order_types,
        "max_orders": min(policy.max_orders or len(batch_request.orders), len(batch_request.orders)),
        "max_quantity_per_order": min(policy.max_quantity_per_order or max_quantity, max_quantity),
        "max_notional_per_order": policy.max_notional_per_order,
        "max_gross_notional": policy.max_gross_notional,
        "max_net_notional": policy.max_net_notional,
    }


def _append_scope_reasons(
    reasons: list[str],
    policy: PaperExecutionPolicyCeiling,
    grant: PaperExecutionGrant,
    batch_request: PaperBatchRequest,
    order: PaperExecutionOrder,
) -> None:
    scope = grant.scope
    if batch_request.strategy_key not in tuple(scope.get("strategies", ())):
        reasons.append("strategy_outside_grant_scope")
    if batch_request.strategy_key not in policy.permitted_strategies:
        reasons.append("strategy_not_permitted")
    if order.symbol not in tuple(scope.get("symbols", ())):
        reasons.append("symbol_outside_grant_scope")
    if order.symbol not in policy.permitted_symbols:
        reasons.append("symbol_not_permitted")
    if order.side not in tuple(scope.get("sides", ())):
        reasons.append("side_outside_grant_scope")
    if order.side not in policy.permitted_sides:
        reasons.append("side_not_permitted")
    if order.order_type not in tuple(scope.get("order_types", ())):
        reasons.append("order_type_outside_grant_scope")
    if order.order_type not in policy.permitted_order_types:
        reasons.append("order_type_not_permitted")


def _clean_upper_values(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip().upper() for value in values if value.strip()))


def _clean_lower_values(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip().lower() for value in values if value.strip()))


def _safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): item for key, item in value.items()}


def _optional_aware_utc(value: datetime | None) -> datetime | None:
    return _aware_utc(value) if value is not None else None


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _within_market_hours(value: datetime) -> bool:
    current_time = value.time()
    return time(3, 45) <= current_time <= time(10, 0)
