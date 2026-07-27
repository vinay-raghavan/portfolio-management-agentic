from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from .fyers_integration import FyersConnection, FyersOAuthSession


class PostgresFyersIntegrationStore:
    """Tenant-scoped FYERS connection/OAuth metadata store.

    The store intentionally persists only sanitized connection state, hashed
    OAuth state, and PKCE challenge metadata. It never accepts or writes access
    tokens, refresh tokens, client secrets, trading tokens, or PKCE verifiers.
    """

    def __init__(
        self,
        *,
        tenant_id: str,
        connection_factory: Callable[[], Any],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required for FYERS integration storage")
        self._tenant_id = tenant_id
        self._connection_factory = connection_factory
        self._now = now or (lambda: datetime.now(UTC))

    def get_connection(self, *, user_id_hash: str) -> FyersConnection | None:
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        tenant_id,
                        provider,
                        fyers_user_hash,
                        status,
                        daily_auth_expires_at,
                        disconnected_at,
                        metadata,
                        created_at,
                        updated_at
                    FROM fyers_connections
                    WHERE tenant_id = %(tenant_id)s
                      AND provider = 'fyers'
                      AND fyers_user_hash = %(fyers_user_hash)s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """.strip(),
                    {
                        "tenant_id": self._tenant_id,
                        "fyers_user_hash": user_id_hash,
                    },
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_connection(row)

    def upsert_connection(self, connection_state: FyersConnection) -> FyersConnection:
        if connection_state.tenant_id != self._tenant_id:
            raise ValueError("FYERS connection tenant does not match store tenant")
        metadata = {
            "credential_status": connection_state.credential_status,
            "data_app_mode": connection_state.data_app_mode,
            "daily_auth_required": connection_state.daily_auth_required,
            "notes": list(connection_state.notes),
        }
        params = {
            "connection_id": connection_state.connection_id,
            "tenant_id": self._tenant_id,
            "provider": "fyers",
            "fyers_user_hash": connection_state.user_id_hash,
            "credential_ref": None,
            "scopes": ["data:read", "account:read"],
            "status": connection_state.status,
            "daily_auth_expires_at": _optional_aware_utc(connection_state.expires_at),
            "disconnected_at": _optional_aware_utc(connection_state.disconnected_at),
            "metadata": metadata,
            "created_at": _aware_utc(connection_state.created_at),
            "updated_at": _aware_utc(connection_state.updated_at),
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO fyers_connections (
                        id,
                        tenant_id,
                        provider,
                        fyers_user_hash,
                        credential_ref,
                        scopes,
                        status,
                        daily_auth_expires_at,
                        disconnected_at,
                        metadata,
                        created_at,
                        updated_at
                    ) VALUES (
                        %(connection_id)s,
                        %(tenant_id)s,
                        %(provider)s,
                        %(fyers_user_hash)s,
                        %(credential_ref)s,
                        %(scopes)s,
                        %(status)s,
                        %(daily_auth_expires_at)s,
                        %(disconnected_at)s,
                        %(metadata)s,
                        %(created_at)s,
                        %(updated_at)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        fyers_user_hash = EXCLUDED.fyers_user_hash,
                        credential_ref = NULL,
                        scopes = EXCLUDED.scopes,
                        status = EXCLUDED.status,
                        daily_auth_expires_at = EXCLUDED.daily_auth_expires_at,
                        disconnected_at = EXCLUDED.disconnected_at,
                        metadata = EXCLUDED.metadata,
                        updated_at = EXCLUDED.updated_at
                    """.strip(),
                    params,
                )
            connection.commit()
        return connection_state

    def upsert_oauth_session(self, session: FyersOAuthSession) -> FyersOAuthSession:
        if session.tenant_id != self._tenant_id:
            raise ValueError("FYERS OAuth session tenant does not match store tenant")
        params = {
            "tenant_id": self._tenant_id,
            "connection_id": session.connection_id,
            "state_hash": session.state_hash,
            "code_challenge": session.code_challenge,
            "expires_at": _aware_utc(session.expires_at),
            "created_at": _aware_utc(session.created_at),
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO fyers_oauth_sessions (
                        tenant_id,
                        connection_id,
                        state_hash,
                        code_challenge,
                        expires_at,
                        consumed_at,
                        created_at
                    ) VALUES (
                        %(tenant_id)s,
                        %(connection_id)s,
                        %(state_hash)s,
                        %(code_challenge)s,
                        %(expires_at)s,
                        NULL,
                        %(created_at)s
                    )
                    ON CONFLICT (tenant_id, state_hash) DO UPDATE SET
                        connection_id = EXCLUDED.connection_id,
                        code_challenge = EXCLUDED.code_challenge,
                        expires_at = EXCLUDED.expires_at,
                        consumed_at = NULL,
                        created_at = EXCLUDED.created_at
                    """.strip(),
                    params,
                )
            connection.commit()
        return session

    def pop_oauth_session(
        self,
        *,
        state_hash: str,
        connection_id: str,
    ) -> FyersOAuthSession | None:
        now = _aware_utc(self._now())
        params = {
            "tenant_id": self._tenant_id,
            "state_hash": state_hash,
            "connection_id": connection_id,
            "now": now,
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        tenant_id,
                        connection_id,
                        state_hash,
                        code_challenge,
                        expires_at,
                        created_at
                    FROM fyers_oauth_sessions
                    WHERE tenant_id = %(tenant_id)s
                      AND state_hash = %(state_hash)s
                      AND connection_id = %(connection_id)s
                      AND consumed_at IS NULL
                      AND expires_at > %(now)s
                    LIMIT 1
                    """.strip(),
                    params,
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                cursor.execute(
                    """
                    UPDATE fyers_oauth_sessions
                    SET consumed_at = %(consumed_at)s
                    WHERE tenant_id = %(tenant_id)s
                      AND state_hash = %(state_hash)s
                      AND connection_id = %(connection_id)s
                      AND consumed_at IS NULL
                    """.strip(),
                    {
                        "tenant_id": self._tenant_id,
                        "state_hash": state_hash,
                        "connection_id": connection_id,
                        "consumed_at": now,
                    },
                )
            connection.commit()
        return _row_to_session(row)

    def clear_oauth_sessions(self, *, connection_id: str) -> None:
        consumed_at = _aware_utc(self._now())
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE fyers_oauth_sessions
                    SET consumed_at = %(consumed_at)s
                    WHERE tenant_id = %(tenant_id)s
                      AND connection_id = %(connection_id)s
                      AND consumed_at IS NULL
                    """.strip(),
                    {
                        "tenant_id": self._tenant_id,
                        "connection_id": connection_id,
                        "consumed_at": consumed_at,
                    },
                )
            connection.commit()


def _row_to_connection(row: Mapping[str, Any]) -> FyersConnection:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
    return FyersConnection(
        tenant_id=str(row["tenant_id"]),
        connection_id=str(row["id"]),
        provider=str(row.get("provider") or "fyers"),
        user_id_hash=str(row.get("fyers_user_hash") or ""),
        status=str(row.get("status") or "disconnected"),
        credential_status=str(metadata.get("credential_status") or "not_loaded"),
        data_app_mode=str(metadata.get("data_app_mode") or "read_only"),
        daily_auth_required=bool(metadata.get("daily_auth_required", True)),
        created_at=_aware_utc(row["created_at"]),
        updated_at=_aware_utc(row["updated_at"]),
        expires_at=_optional_aware_utc(row.get("daily_auth_expires_at")),
        disconnected_at=_optional_aware_utc(row.get("disconnected_at")),
        notes=tuple(str(note) for note in metadata.get("notes", ())),
    )


def _row_to_session(row: Mapping[str, Any]) -> FyersOAuthSession:
    return FyersOAuthSession(
        tenant_id=str(row["tenant_id"]),
        connection_id=str(row["connection_id"]),
        state_hash=str(row["state_hash"]),
        code_challenge=str(row["code_challenge"]),
        expires_at=_aware_utc(row["expires_at"]),
        created_at=_aware_utc(row["created_at"]),
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return _aware_utc(value)
