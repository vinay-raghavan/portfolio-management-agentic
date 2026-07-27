from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .paper_execution import (
    DeterministicPaperExecutionWorker,
    PaperBatchRequest,
    PaperExecutionDecision,
    PaperExecutionGrant,
    PaperExecutionOrder,
    PaperExecutionPolicyCeiling,
    PaperExecutionWorkerRequest,
    PaperExecutionWorkItem,
)


class PaperExecutionQueueStore(Protocol):
    def claim_next_execution_work_item(
        self,
        *,
        worker_id: str,
        now: datetime | None = None,
    ) -> PaperExecutionWorkItem | None: ...

    def claim_execution_work_item(
        self,
        *,
        work_item_id: str,
        worker_id: str,
        now: datetime | None = None,
    ) -> PaperExecutionWorkItem | None: ...

    def get_grant(self, grant_id: str) -> PaperExecutionGrant | None: ...

    def get_batch_request(self, batch_request_id: str) -> PaperBatchRequest | None: ...

    def get_policy_ceiling(
        self,
        policy_id: str,
    ) -> PaperExecutionPolicyCeiling | None: ...

    def execution_decision_exists(self, idempotency_key: str) -> bool: ...

    def record_execution_decision(
        self,
        *,
        grant: PaperExecutionGrant,
        batch_request: PaperBatchRequest,
        order: PaperExecutionOrder,
        decision: PaperExecutionDecision,
        fill_price: float,
        exposure_after: Mapping[str, Any],
    ) -> PaperExecutionDecision: ...

    def complete_execution_work_item(
        self,
        *,
        work_item_id: str,
        decision: PaperExecutionDecision,
        now: datetime | None = None,
    ) -> PaperExecutionWorkItem | None: ...


@dataclass(frozen=True)
class PaperExecutionQueueProcessorResult:
    status: str
    work_item_id: str | None
    decision: PaperExecutionDecision | None
    reason: str | None = None


@dataclass(frozen=True)
class PaperExecutionQueueProcessor:
    """Process claimed paper-only execution work items with deterministic tools."""

    store: PaperExecutionQueueStore
    worker_id: str
    now: Callable[[], datetime] | None = None

    def process_once(
        self,
        *,
        work_item_id: str | None = None,
    ) -> PaperExecutionQueueProcessorResult:
        current_time = _aware_utc(self.now() if self.now is not None else _utc_now())
        claimed = self._claim_work_item(work_item_id=work_item_id, now=current_time)
        if claimed is None:
            return PaperExecutionQueueProcessorResult(
                status="no_work",
                work_item_id=work_item_id,
                decision=None,
                reason="no_claimable_work_item",
            )
        decision = self._execute_claimed_work_item(claimed, now=current_time)
        completed = self.store.complete_execution_work_item(
            work_item_id=claimed.work_item_id,
            decision=decision,
            now=current_time,
        )
        status = "processed" if decision.status == "accepted" else "failed"
        if completed is None:
            return PaperExecutionQueueProcessorResult(
                status="failed",
                work_item_id=claimed.work_item_id,
                decision=decision,
                reason="completion_failed",
            )
        return PaperExecutionQueueProcessorResult(
            status=status,
            work_item_id=claimed.work_item_id,
            decision=decision,
        )

    def _claim_work_item(
        self,
        *,
        work_item_id: str | None,
        now: datetime,
    ) -> PaperExecutionWorkItem | None:
        if work_item_id is not None:
            return self.store.claim_execution_work_item(
                work_item_id=work_item_id,
                worker_id=self.worker_id,
                now=now,
            )
        return self.store.claim_next_execution_work_item(
            worker_id=self.worker_id,
            now=now,
        )

    def _execute_claimed_work_item(
        self,
        work_item: PaperExecutionWorkItem,
        *,
        now: datetime,
    ) -> PaperExecutionDecision:
        try:
            _reject_sensitive_payload(work_item.to_dict())
            grant = self.store.get_grant(work_item.grant_id)
            if grant is None:
                return _rejected_work_item_decision(
                    work_item,
                    reason="grant_not_found",
                    now=now,
                )
            batch = self.store.get_batch_request(work_item.batch_request_id)
            if batch is None:
                return _rejected_work_item_decision(
                    work_item,
                    reason="batch_request_not_found",
                    now=now,
                )
            policy = self.store.get_policy_ceiling(grant.policy_ceiling_id)
            if policy is None:
                return _rejected_work_item_decision(
                    work_item,
                    reason="policy_not_found",
                    now=now,
                )
            order = _order_from_work_item(work_item, batch)
            payload = _validated_payload(work_item.payload)
            used_keys = (
                {work_item.idempotency_key}
                if self.store.execution_decision_exists(work_item.idempotency_key)
                else set()
            )
            worker = DeterministicPaperExecutionWorker(
                record_decision=lambda decision, worker_request: self.store.record_execution_decision(
                    grant=worker_request.grant,
                    batch_request=worker_request.batch_request,
                    order=worker_request.order,
                    decision=decision,
                    fill_price=worker_request.quote_price,
                    exposure_after=worker_request.exposure_after or {},
                )
            )
            return worker.execute(
                PaperExecutionWorkerRequest(
                    policy=policy,
                    grant=grant,
                    batch_request=batch,
                    order=order,
                    idempotency_key=work_item.idempotency_key,
                    quote_price=payload["quote_price"],
                    quote_as_of=payload["quote_as_of"],
                    now=payload["now"],
                    used_idempotency_keys=used_keys,
                    available_cash=payload["available_cash"],
                    current_gross_notional=_float_mapping_value(
                        grant.consumed_capacity,
                        "gross_notional",
                    ),
                    current_net_notional=_float_mapping_value(
                        grant.consumed_capacity,
                        "net_notional",
                    ),
                    kill_switch_active=payload["kill_switch_active"],
                    exposure_after=payload["exposure_after"],
                )
            )
        except (TypeError, ValueError, KeyError):
            return _rejected_work_item_decision(
                work_item,
                reason="invalid_work_item_payload",
                now=now,
            )


def _order_from_work_item(
    work_item: PaperExecutionWorkItem,
    batch: PaperBatchRequest,
) -> PaperExecutionOrder:
    batch_id, separator, index_value = work_item.order_id.partition(":")
    if not separator or batch_id != batch.batch_request_id:
        raise ValueError("paper execution work item order_id does not match batch")
    order_index = int(index_value)
    if order_index < 0 or order_index >= len(batch.orders):
        raise ValueError("paper execution work item order index is invalid")
    return batch.orders[order_index]


def _validated_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    _reject_sensitive_payload(payload)
    return {
        "quote_price": float(payload["quote_price"]),
        "quote_as_of": _required_datetime(payload["quote_as_of"]),
        "now": _required_datetime(payload["now"]),
        "available_cash": _optional_float(payload.get("available_cash")),
        "kill_switch_active": bool(payload.get("kill_switch_active", False)),
        "exposure_after": _mapping_value(payload.get("exposure_after")),
    }


def _rejected_work_item_decision(
    work_item: PaperExecutionWorkItem,
    *,
    reason: str,
    now: datetime,
) -> PaperExecutionDecision:
    return PaperExecutionDecision(
        status="rejected",
        reasons=(reason,),
        fill=None,
        audit_event={
            "event_type": "paper_execution_rejected",
            "actor": "deterministic_paper_executor",
            "created_at": now.isoformat(),
            "grant_id": work_item.grant_id,
            "idempotency_key": work_item.idempotency_key,
            "work_item_id": work_item.work_item_id,
            "mode": "paper",
            "reasons": (reason,),
        },
    )


def _mapping_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("expected mapping payload")
    return {str(key): item for key, item in value.items()}


def _float_mapping_value(payload: Mapping[str, Any], key: str) -> float:
    try:
        return float(payload.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _required_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return _aware_utc(value)
    if isinstance(value, str):
        return _aware_utc(datetime.fromisoformat(value))
    raise ValueError("expected datetime payload")


def _reject_sensitive_payload(payload: object) -> None:
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
        raise ValueError("paper execution queue payload contains sensitive data")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
