from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from portfolio_domain import (
    FyersConnection,
    FyersOAuthSession,
    PostgresFyersIntegrationStore,
    actor_hash,
)


NOW = datetime(2026, 7, 27, 9, 45, tzinfo=timezone.utc)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "oidc-subject-1"
CONNECTION_ID = "22222222-2222-2222-2222-222222222222"


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

    def fetchone(self):
        if not self._rows:
            return None
        return self._rows.pop(0)


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


def _store(cursor: _FakeCursor, connection: _FakeConnection) -> PostgresFyersIntegrationStore:
    return PostgresFyersIntegrationStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
        now=lambda: NOW,
    )


def _connection() -> FyersConnection:
    return FyersConnection.disconnected(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        connection_id=CONNECTION_ID,
        now=NOW,
    ).oauth_started(expires_at=NOW + timedelta(minutes=10), now=NOW)


def test_migration_adds_hashed_fyers_oauth_sessions_table() -> None:
    migration = Path(
        "infra/db/alembic/versions/20260727_0006_fyers_oauth_sessions.py"
    ).read_text()

    assert 'revision = "20260727_0006"' in migration
    assert 'down_revision = "20260727_0005"' in migration
    assert "fyers_oauth_sessions" in migration
    assert "state_hash" in migration
    assert "code_challenge" in migration
    assert "connection_id" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "tenant_isolation_{table_name}" in migration
    assert "code_verifier" not in migration
    assert "access_token" not in migration
    assert "refresh_token" not in migration
    assert "client_secret" not in migration


def test_postgres_fyers_store_upserts_connection_without_credentials_or_verifier() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    stored = store.upsert_connection(_connection())

    sql, params = cursor.executed[0]
    serialized = f"{sql} {params}".lower()
    assert "INSERT INTO fyers_connections" in sql
    assert "ON CONFLICT (id)" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["connection_id"] == CONNECTION_ID
    assert params["provider"] == "fyers"
    assert params["fyers_user_hash"] == actor_hash(tenant_id=TENANT_ID, user_id=USER_ID)
    assert params["credential_ref"] is None
    assert params["scopes"] == ["data:read", "account:read"]
    assert params["status"] == "reconnect_required"
    assert params["metadata"]["credential_status"] == "authorization_required"
    assert params["metadata"]["data_app_mode"] == "read_only"
    assert stored.connection_id == CONNECTION_ID
    assert connection.committed is True
    assert "code_verifier" not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "client_secret" not in serialized
    assert "trading_token" not in serialized


def test_postgres_fyers_store_reads_connection_by_tenant_and_user_hash() -> None:
    user_hash = actor_hash(tenant_id=TENANT_ID, user_id=USER_ID)
    cursor = _FakeCursor(
        rows=[
            {
                "id": CONNECTION_ID,
                "tenant_id": TENANT_ID,
                "provider": "fyers",
                "fyers_user_hash": user_hash,
                "status": "reconnect_required",
                "daily_auth_expires_at": NOW + timedelta(minutes=10),
                "disconnected_at": None,
                "metadata": {
                    "credential_status": "authorization_required",
                    "data_app_mode": "read_only",
                    "daily_auth_required": True,
                    "notes": ["redacted state only"],
                },
                "created_at": NOW,
                "updated_at": NOW,
            }
        ]
    )
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    loaded = store.get_connection(user_id_hash=user_hash)

    sql, params = cursor.executed[0]
    assert "FROM fyers_connections" in sql
    assert "tenant_id = %(tenant_id)s" in sql
    assert "fyers_user_hash = %(fyers_user_hash)s" in sql
    assert params == {"tenant_id": TENANT_ID, "fyers_user_hash": user_hash}
    assert loaded is not None
    assert loaded.connection_id == CONNECTION_ID
    assert loaded.credential_status == "authorization_required"
    assert "access_token" not in str(loaded.to_dict()).lower()


def test_postgres_fyers_store_pops_actor_scoped_oauth_session_once() -> None:
    session = FyersOAuthSession.create(
        tenant_id=TENANT_ID,
        connection_id=CONNECTION_ID,
        state="browser-state",
        code_challenge="pkce-challenge",
        now=NOW,
    )
    cursor = _FakeCursor(
        rows=[
            {
                "tenant_id": TENANT_ID,
                "connection_id": CONNECTION_ID,
                "state_hash": session.state_hash,
                "code_challenge": "pkce-challenge",
                "expires_at": NOW + timedelta(minutes=10),
                "created_at": NOW,
            }
        ]
    )
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    store.upsert_oauth_session(session)
    popped = store.pop_oauth_session(
        state_hash=session.state_hash,
        connection_id=CONNECTION_ID,
    )

    insert_sql, insert_params = cursor.executed[0]
    select_sql, select_params = cursor.executed[1]
    update_sql, update_params = cursor.executed[2]
    serialized = f"{cursor.executed}".lower()
    assert "INSERT INTO fyers_oauth_sessions" in insert_sql
    assert insert_params["state_hash"] == session.state_hash
    assert insert_params["code_challenge"] == "pkce-challenge"
    assert "code_verifier" not in str(insert_params).lower()
    assert "FROM fyers_oauth_sessions" in select_sql
    assert select_params["tenant_id"] == TENANT_ID
    assert select_params["state_hash"] == session.state_hash
    assert select_params["connection_id"] == CONNECTION_ID
    assert "UPDATE fyers_oauth_sessions" in update_sql
    assert update_params["consumed_at"] == NOW
    assert popped == session
    assert connection.committed is True
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "client_secret" not in serialized


def test_postgres_fyers_store_clears_connection_sessions_without_cross_tenant_scope() -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = _store(cursor, connection)

    store.clear_oauth_sessions(connection_id=CONNECTION_ID)

    sql, params = cursor.executed[0]
    assert "UPDATE fyers_oauth_sessions" in sql
    assert "tenant_id = %(tenant_id)s" in sql
    assert "connection_id = %(connection_id)s" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["connection_id"] == CONNECTION_ID
    assert params["consumed_at"] == NOW
    assert connection.committed is True
