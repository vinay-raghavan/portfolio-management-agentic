from __future__ import annotations

from datetime import UTC, datetime

import pytest

from portfolio_domain import PostgresActorIdentityStore


NOW = datetime(2026, 7, 27, 11, 0, tzinfo=UTC)


class _FakeCursor:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.rows = rows or []
        self.executed: list[tuple[str, dict]] = []

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


def test_postgres_actor_identity_store_upserts_issuer_subject_without_raw_profile() -> None:
    cursor = _FakeCursor(
        [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "issuer": "https://issuer.example.com",
                "subject": "oidc-sub-123",
                "email_hash": "sha256:email",
                "display_name": None,
                "last_seen_at": NOW,
                "created_at": NOW,
                "updated_at": NOW,
            }
        ]
    )
    connection = _FakeConnection(cursor)
    store = PostgresActorIdentityStore(
        connection_factory=lambda: connection,
        now=lambda: NOW,
    )

    record = store.upsert_identity(
        issuer="https://issuer.example.com",
        subject="oidc-sub-123",
        email_hash="sha256:email",
    )

    sql, params = cursor.executed[0]
    assert "INSERT INTO actor_identities" in sql
    assert "ON CONFLICT (issuer, subject) DO UPDATE" in sql
    assert "RETURNING" in sql
    assert params == {
        "issuer": "https://issuer.example.com",
        "subject": "oidc-sub-123",
        "email_hash": "sha256:email",
        "display_name": None,
        "now": NOW,
    }
    assert record.actor_identity_id == "11111111-1111-1111-1111-111111111111"
    assert record.issuer == "https://issuer.example.com"
    assert record.subject == "oidc-sub-123"
    assert connection.committed is True
    assert "@" not in str(record.to_dict())


@pytest.mark.parametrize(
    ("issuer", "subject"),
    [
        ("", "oidc-sub-123"),
        ("https://issuer.example.com", ""),
    ],
)
def test_postgres_actor_identity_store_rejects_missing_issuer_or_subject(
    issuer: str,
    subject: str,
) -> None:
    store = PostgresActorIdentityStore(
        connection_factory=lambda: _FakeConnection(_FakeCursor()),
        now=lambda: NOW,
    )

    with pytest.raises(ValueError):
        store.upsert_identity(issuer=issuer, subject=subject)
