from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from portfolio_domain import (
    SessionMemoryPolicy,
    SessionMemoryValidationError,
    PostgresSessionMemoryStore,
    sanitize_session_memory_payload,
)


NOW = datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc)


class _FakeCursor:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.rows = rows or []
        self.executed: list[tuple[str, dict]] = []
        self.description = [(key,) for key in self.rows[0]] if self.rows else []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, sql: str, params: dict) -> None:
        self.executed.append((sql, params))

    def fetchone(self) -> dict | None:
        return self.rows[0] if self.rows else None


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


def test_session_memory_policy_defaults_match_privacy_contract() -> None:
    policy = SessionMemoryPolicy.default()

    assert policy.idle_ttl == timedelta(hours=2)
    assert policy.absolute_ttl == timedelta(hours=24)
    assert policy.max_summary_chars == 2_000
    assert policy.persist_long_term_preferences is False
    assert policy.retain_raw_account_payloads is False


def test_session_memory_sanitizer_allows_compact_summary_and_object_refs_only() -> None:
    payload = sanitize_session_memory_payload(
        summary="User asked for a paper-only risk review of TATAMOTORS.",
        object_refs=(
            {"type": "paper_order", "id": "order-123"},
            {"type": "research_document", "id": "doc-456", "version": "v1"},
        ),
    )

    assert payload.summary == "User asked for a paper-only risk review of TATAMOTORS."
    assert payload.object_refs == (
        {"type": "paper_order", "id": "order-123"},
        {"type": "research_document", "id": "doc-456", "version": "v1"},
    )


@pytest.mark.parametrize(
    "summary",
    [
        "Remember my long-term preference for aggressive intraday trades.",
        "Private note: I keep my emergency fund at this bank.",
        "Raw account payload: {'holdings': [{'isin': 'secret'}]}",
        "FYERS access_token=should-not-store",
    ],
)
def test_session_memory_sanitizer_rejects_forbidden_summary_content(summary: str) -> None:
    with pytest.raises(SessionMemoryValidationError):
        sanitize_session_memory_payload(summary=summary, object_refs=())


def test_session_memory_sanitizer_rejects_raw_object_refs() -> None:
    with pytest.raises(SessionMemoryValidationError):
        sanitize_session_memory_payload(
            summary="Summarized paper-only discussion.",
            object_refs=({"type": "broker_account_snapshot", "raw_payload": {"funds": 1}},),
        )


def test_postgres_session_memory_store_upserts_tenant_scoped_summary_with_ttls() -> None:
    cursor = _FakeCursor(
        [
            {
                "id": "session-1",
                "tenant_id": "tenant-a",
                "actor_identity_id": "actor-1",
                "request_id": "req-1",
                "summary": "User asked for a paper-only risk review.",
                "object_refs": [{"type": "paper_order", "id": "order-123"}],
                "idle_expires_at": NOW + timedelta(hours=2),
                "absolute_expires_at": NOW + timedelta(hours=24),
                "deleted_at": None,
                "created_at": NOW,
                "updated_at": NOW,
            }
        ]
    )
    connection = _FakeConnection(cursor)
    store = PostgresSessionMemoryStore(
        tenant_id="tenant-a",
        actor_identity_id="actor-1",
        connection_factory=lambda: connection,
        now=lambda: NOW,
    )

    record = store.upsert_summary(
        session_id="session-1",
        request_id="req-1",
        summary="User asked for a paper-only risk review.",
        object_refs=({"type": "paper_order", "id": "order-123"},),
    )

    sql, params = cursor.executed[0]
    assert "INSERT INTO agent_sessions" in sql
    assert "tenant_id" in sql
    assert "actor_identity_id" in sql
    assert "ON CONFLICT (id)" in sql
    assert "WHERE agent_sessions.tenant_id = %(tenant_id)s" in sql
    assert "agent_sessions.actor_identity_id = %(actor_identity_id)s" in sql
    assert params["tenant_id"] == "tenant-a"
    assert params["actor_identity_id"] == "actor-1"
    assert params["idle_expires_at"] == NOW + timedelta(hours=2)
    assert params["absolute_expires_at"] == NOW + timedelta(hours=24)
    assert record.session_id == "session-1"
    assert record.tenant_id == "tenant-a"
    assert record.summary == "User asked for a paper-only risk review."
    assert connection.committed is True
    assert "access_token" not in str(record.to_dict()).lower()


def test_postgres_session_memory_get_filters_tenant_actor_expiry_and_deleted() -> None:
    cursor = _FakeCursor([])
    store = PostgresSessionMemoryStore(
        tenant_id="tenant-a",
        actor_identity_id="actor-1",
        connection_factory=lambda: _FakeConnection(cursor),
        now=lambda: NOW,
    )

    assert store.get("session-1") is None
    sql, params = cursor.executed[0]
    assert "WHERE id = %(session_id)s" in sql
    assert "tenant_id = %(tenant_id)s" in sql
    assert "actor_identity_id = %(actor_identity_id)s" in sql
    assert "deleted_at IS NULL" in sql
    assert "idle_expires_at > %(now)s" in sql
    assert "absolute_expires_at > %(now)s" in sql
    assert params == {
        "session_id": "session-1",
        "tenant_id": "tenant-a",
        "actor_identity_id": "actor-1",
        "now": NOW,
    }


def test_postgres_session_memory_delete_is_tenant_scoped_and_committed() -> None:
    cursor = _FakeCursor([])
    connection = _FakeConnection(cursor)
    store = PostgresSessionMemoryStore(
        tenant_id="tenant-a",
        actor_identity_id="actor-1",
        connection_factory=lambda: connection,
        now=lambda: NOW,
    )

    store.delete("session-1")

    sql, params = cursor.executed[0]
    assert "UPDATE agent_sessions" in sql
    assert "deleted_at = %(now)s" in sql
    assert "tenant_id = %(tenant_id)s" in sql
    assert "actor_identity_id = %(actor_identity_id)s" in sql
    assert params == {
        "session_id": "session-1",
        "tenant_id": "tenant-a",
        "actor_identity_id": "actor-1",
        "now": NOW,
    }
    assert connection.committed is True
