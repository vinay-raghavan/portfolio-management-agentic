from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from .config import ModelProvider, ModelUsageBudgetDecision, ModelUsageEvent


class PostgresModelUsageStore:
    """Tenant-scoped durable store for metric-only model usage telemetry."""

    def __init__(
        self,
        *,
        tenant_id: str,
        connection_factory: Callable[[], Any],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required for Postgres model usage telemetry")
        self._tenant_id = tenant_id
        self._connection_factory = connection_factory
        self._now = now or (lambda: datetime.now(UTC))

    def record(
        self,
        event: ModelUsageEvent,
        decision: ModelUsageBudgetDecision,
    ) -> None:
        created_at = _aware_utc(self._now())
        params = {
            "tenant_id": self._tenant_id,
            "request_id": event.request_id,
            "provider": event.provider.value,
            "model": event.model,
            "route": event.route,
            "prompt_tokens": event.prompt_tokens,
            "output_tokens": event.output_tokens,
            "tool_calls": event.tool_calls,
            "queue_wait_ms": event.queue_wait_ms,
            "latency_ms": event.latency_ms,
            "retries": event.retries,
            "allowed": decision.allowed,
            "violations": list(decision.violations),
            "prompt_budget_tokens": decision.prompt_budget_tokens,
            "output_budget_tokens": decision.output_budget_tokens,
            "tool_call_budget": decision.tool_call_budget,
            "context_window_tokens": decision.context_window_tokens,
            "max_request_input_tokens": decision.max_request_input_tokens,
            "prompt_utilization": decision.prompt_utilization,
            "output_utilization": decision.output_utilization,
            "tool_call_utilization": decision.tool_call_utilization,
            "context_utilization": decision.context_utilization,
            "created_at": created_at,
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO model_usage_events (
                        tenant_id,
                        request_id,
                        provider,
                        model,
                        route,
                        prompt_tokens,
                        output_tokens,
                        tool_calls,
                        queue_wait_ms,
                        latency_ms,
                        retries,
                        allowed,
                        violations,
                        prompt_budget_tokens,
                        output_budget_tokens,
                        tool_call_budget,
                        context_window_tokens,
                        max_request_input_tokens,
                        prompt_utilization,
                        output_utilization,
                        tool_call_utilization,
                        context_utilization,
                        created_at
                    ) VALUES (
                        %(tenant_id)s,
                        %(request_id)s,
                        %(provider)s,
                        %(model)s,
                        %(route)s,
                        %(prompt_tokens)s,
                        %(output_tokens)s,
                        %(tool_calls)s,
                        %(queue_wait_ms)s,
                        %(latency_ms)s,
                        %(retries)s,
                        %(allowed)s,
                        %(violations)s,
                        %(prompt_budget_tokens)s,
                        %(output_budget_tokens)s,
                        %(tool_call_budget)s,
                        %(context_window_tokens)s,
                        %(max_request_input_tokens)s,
                        %(prompt_utilization)s,
                        %(output_utilization)s,
                        %(tool_call_utilization)s,
                        %(context_utilization)s,
                        %(created_at)s
                    )
                    ON CONFLICT (tenant_id, request_id) DO NOTHING
                    """.strip(),
                    params,
                )
            connection.commit()

    def list_recent(self, *, limit: int = 500) -> tuple[ModelUsageEvent, ...]:
        bounded_limit = max(1, min(int(limit), 5_000))
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        provider,
                        model,
                        route,
                        prompt_tokens,
                        output_tokens,
                        tool_calls,
                        queue_wait_ms,
                        latency_ms,
                        retries,
                        request_id
                    FROM model_usage_events
                    WHERE tenant_id = %(tenant_id)s
                    ORDER BY created_at DESC
                    LIMIT %(limit)s
                    """.strip(),
                    {
                        "tenant_id": self._tenant_id,
                        "limit": bounded_limit,
                    },
                )
                rows = cursor.fetchall()
        return tuple(_row_to_event(row) for row in rows)


def _row_to_event(row: Mapping[str, Any]) -> ModelUsageEvent:
    return ModelUsageEvent(
        provider=ModelProvider(str(row["provider"])),
        model=str(row["model"]),
        route=str(row["route"]),
        prompt_tokens=int(row["prompt_tokens"]),
        output_tokens=int(row["output_tokens"]),
        tool_calls=int(row["tool_calls"]),
        queue_wait_ms=int(row["queue_wait_ms"]),
        latency_ms=int(row["latency_ms"]),
        retries=int(row["retries"]),
        request_id=str(row["request_id"]),
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
