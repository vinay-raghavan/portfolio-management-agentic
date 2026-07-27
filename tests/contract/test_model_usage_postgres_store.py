from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from portfolio_model_provider import (
    ModelProvider,
    ModelUsageBudgetDecision,
    ModelUsageEvent,
    PostgresModelUsageStore,
)


TENANT_ID = "11111111-1111-1111-1111-111111111111"
NOW = datetime(2026, 7, 27, 9, 30, tzinfo=timezone.utc)


class _FakeCursor:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.executed: list[tuple[str, dict]] = []
        self._rows = rows or []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, sql: str, params: dict) -> None:
        self.executed.append((sql, params))

    def fetchall(self):
        return self._rows


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


def _event() -> ModelUsageEvent:
    return ModelUsageEvent(
        provider=ModelProvider.OLLAMA,
        model="llama3.1:8b",
        route="technical_analysis",
        prompt_tokens=3200,
        output_tokens=700,
        tool_calls=4,
        queue_wait_ms=120,
        latency_ms=2400,
        retries=1,
        request_id="req-usage-1",
    )


def _decision() -> ModelUsageBudgetDecision:
    return ModelUsageBudgetDecision(
        provider=ModelProvider.OLLAMA,
        model="llama3.1:8b",
        route="technical_analysis",
        allowed=True,
        violations=(),
        prompt_budget_tokens=6553,
        output_budget_tokens=1500,
        tool_call_budget=5,
        context_window_tokens=8192,
        max_request_input_tokens=6553,
        prompt_utilization=0.488,
        output_utilization=0.466,
        tool_call_utilization=0.8,
        context_utilization=0.476,
    )


def test_migration_adds_tenant_scoped_model_usage_events_table() -> None:
    migration = Path(
        "infra/db/alembic/versions/20260727_0005_model_usage_events.py"
    ).read_text()

    assert 'revision = "20260727_0005"' in migration
    assert 'down_revision = "20260727_0004"' in migration
    assert "model_usage_events" in migration
    assert "tenant_id" in migration
    assert "request_id" in migration
    assert "violations" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "tenant_isolation_{table_name}" in migration
    assert "DROP POLICY IF EXISTS" in migration
    assert "raw_prompt" not in migration
    assert "raw_response" not in migration


def test_postgres_model_usage_store_records_metric_only_budget_decision() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = PostgresModelUsageStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
        now=lambda: NOW,
    )

    store.record(_event(), _decision())

    sql, params = cursor.executed[0]
    serialized = f"{sql} {params}".lower()
    assert "INSERT INTO model_usage_events" in sql
    assert "tenant_id" in sql
    assert "ON CONFLICT (tenant_id, request_id) DO NOTHING" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["provider"] == "ollama"
    assert params["model"] == "llama3.1:8b"
    assert params["route"] == "technical_analysis"
    assert params["prompt_tokens"] == 3200
    assert params["output_tokens"] == 700
    assert params["violations"] == []
    assert params["created_at"] == NOW
    assert connection.committed is True
    assert "raw_prompt" not in serialized
    assert "raw_response" not in serialized
    assert "access_token" not in serialized
    assert "secret" not in serialized


def test_postgres_model_usage_store_lists_recent_events_without_payload_columns() -> None:
    cursor = _FakeCursor(
        rows=[
            {
                "provider": "ollama",
                "model": "llama3.1:8b",
                "route": "research",
                "prompt_tokens": 1000,
                "output_tokens": 200,
                "tool_calls": 2,
                "queue_wait_ms": 25,
                "latency_ms": 900,
                "retries": 0,
                "request_id": "req-usage-2",
            }
        ]
    )
    connection = _FakeConnection(cursor)
    store = PostgresModelUsageStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
    )

    events = store.list_recent(limit=50)

    sql, params = cursor.executed[0]
    serialized = f"{sql} {params}".lower()
    assert "SELECT" in sql
    assert "FROM model_usage_events" in sql
    assert "tenant_id = %(tenant_id)s" in sql
    assert "ORDER BY created_at DESC" in sql
    assert params == {"tenant_id": TENANT_ID, "limit": 50}
    assert events == (
        ModelUsageEvent(
            provider=ModelProvider.OLLAMA,
            model="llama3.1:8b",
            route="research",
            prompt_tokens=1000,
            output_tokens=200,
            tool_calls=2,
            queue_wait_ms=25,
            latency_ms=900,
            retries=0,
            request_id="req-usage-2",
        ),
    )
    assert "raw_prompt" not in serialized
    assert "raw_response" not in serialized
    assert "secret" not in serialized
