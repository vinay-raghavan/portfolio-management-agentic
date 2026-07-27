from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Protocol


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def actor_hash(*, tenant_id: str, user_id: str) -> str:
    digest = sha256(f"{tenant_id}:{user_id}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


@dataclass(frozen=True)
class FyersConnection:
    tenant_id: str
    connection_id: str
    provider: str
    user_id_hash: str
    status: str
    credential_status: str
    credential_ref: str | None
    data_app_mode: str
    daily_auth_required: bool
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    disconnected_at: datetime | None
    notes: tuple[str, ...]

    @classmethod
    def disconnected(
        cls,
        *,
        tenant_id: str,
        user_id: str,
        connection_id: str,
        now: datetime | None = None,
    ) -> FyersConnection:
        timestamp = now or utc_now()
        return cls(
            tenant_id=tenant_id,
            connection_id=connection_id,
            provider="fyers",
            user_id_hash=actor_hash(tenant_id=tenant_id, user_id=user_id),
            status="disconnected",
            credential_status="not_loaded",
            credential_ref=None,
            data_app_mode="read_only",
            daily_auth_required=True,
            created_at=timestamp,
            updated_at=timestamp,
            expires_at=None,
            disconnected_at=timestamp,
            notes=(
                "FYERS credentials are not loaded into prompts, traces, MCP arguments, or responses.",
                "OAuth and disconnect operations are protected human-facing API actions.",
            ),
        )

    def oauth_started(
        self,
        *,
        expires_at: datetime,
        now: datetime | None = None,
    ) -> FyersConnection:
        return replace(
            self,
            status="reconnect_required",
            credential_status="authorization_required",
            updated_at=now or utc_now(),
            expires_at=expires_at,
            disconnected_at=None,
            notes=(
                "Daily FYERS authorization is required for the data-only connection.",
                "PKCE verifier is retained server-side only and is never returned.",
            ),
        )

    def callback_recorded(self, *, now: datetime | None = None) -> FyersConnection:
        return replace(
            self,
            status="reconnect_required",
            credential_status="token_exchange_not_configured",
            credential_ref=None,
            updated_at=now or utc_now(),
            notes=(
                "Authorization callback was received.",
                "Credential-vault token exchange is not enabled in this local safe API slice.",
            ),
        )

    def disconnected_copy(self, *, now: datetime | None = None) -> FyersConnection:
        timestamp = now or utc_now()
        return replace(
            self,
            status="disconnected",
            credential_status="not_loaded",
            credential_ref=None,
            updated_at=timestamp,
            expires_at=None,
            disconnected_at=timestamp,
            notes=(
                "Connection disconnected by authenticated human-facing API request.",
                "No provider token or live-order capability is retained here.",
            ),
        )

    def with_credential_ref(
        self,
        *,
        credential_ref: str,
        expires_at: datetime | None = None,
        now: datetime | None = None,
    ) -> FyersConnection:
        return replace(
            self,
            status="connected",
            credential_status="vault_reference_configured",
            credential_ref=credential_ref,
            updated_at=now or utc_now(),
            expires_at=expires_at or self.expires_at,
            disconnected_at=None,
            notes=(
                "FYERS token material is stored in the configured credential vault.",
                "Only an opaque vault reference is persisted in Postgres.",
                "The connection remains read-only and data-app scoped.",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "connection_id": self.connection_id,
            "provider": self.provider,
            "user_id_hash": self.user_id_hash,
            "status": self.status,
            "credential_status": self.credential_status,
            "credential_ref_configured": self.credential_ref is not None,
            "data_app_mode": self.data_app_mode,
            "daily_auth_required": self.daily_auth_required,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "disconnected_at": (
                self.disconnected_at.isoformat() if self.disconnected_at else None
            ),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class FyersOAuthSession:
    tenant_id: str
    connection_id: str
    state_hash: str
    code_challenge: str
    expires_at: datetime
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        connection_id: str,
        state: str,
        code_challenge: str,
        now: datetime | None = None,
        ttl: timedelta = timedelta(minutes=10),
    ) -> FyersOAuthSession:
        timestamp = now or utc_now()
        return cls(
            tenant_id=tenant_id,
            connection_id=connection_id,
            state_hash=hash_oauth_state(state),
            code_challenge=code_challenge,
            expires_at=timestamp + ttl,
            created_at=timestamp,
        )

    def active(self, *, now: datetime | None = None) -> bool:
        return self.expires_at > (now or utc_now())


@dataclass(frozen=True, repr=False)
class FyersPkceVerifierRecord:
    tenant_id: str
    connection_id: str
    state_hash: str
    code_verifier: str
    expires_at: datetime
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        session: FyersOAuthSession,
        code_verifier: str,
    ) -> FyersPkceVerifierRecord:
        if not code_verifier.strip():
            raise ValueError("FYERS PKCE code_verifier is required")
        return cls(
            tenant_id=session.tenant_id,
            connection_id=session.connection_id,
            state_hash=session.state_hash,
            code_verifier=code_verifier,
            expires_at=session.expires_at,
            created_at=session.created_at,
        )

    def __repr__(self) -> str:
        return (
            "FyersPkceVerifierRecord("
            f"tenant_id={self.tenant_id!r}, "
            f"connection_id={self.connection_id!r}, "
            f"state_hash={self.state_hash!r}, "
            "code_verifier=<redacted>, "
            f"expires_at={self.expires_at.isoformat()!r})"
        )

    def active(self, *, now: datetime | None = None) -> bool:
        return self.expires_at > (now or utc_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "connection_id": self.connection_id,
            "state_hash": self.state_hash,
            "code_verifier_configured": True,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


class FyersPkceVerifierCache(Protocol):
    def store(
        self,
        *,
        session: FyersOAuthSession,
        code_verifier: str,
    ) -> FyersPkceVerifierRecord:
        ...

    def pop(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        state_hash: str,
    ) -> str | None:
        ...

    def clear_connection(self, *, tenant_id: str, connection_id: str) -> None:
        ...

    def to_dict(self) -> dict[str, Any]:
        ...


class InMemoryFyersPkceVerifierCache:
    def __init__(self, *, now: Any | None = None) -> None:
        self._records: dict[tuple[str, str, str], FyersPkceVerifierRecord] = {}
        self._now = now or utc_now

    def store(
        self,
        *,
        session: FyersOAuthSession,
        code_verifier: str,
    ) -> FyersPkceVerifierRecord:
        record = FyersPkceVerifierRecord.create(
            session=session,
            code_verifier=code_verifier,
        )
        self._records[
            _verifier_key(record.tenant_id, record.connection_id, record.state_hash)
        ] = record
        return record

    def pop(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        state_hash: str,
    ) -> str | None:
        record = self._records.pop(
            _verifier_key(tenant_id, connection_id, state_hash),
            None,
        )
        if record is None or not record.active(now=self._now()):
            return None
        return record.code_verifier

    def clear_connection(self, *, tenant_id: str, connection_id: str) -> None:
        for key in tuple(self._records):
            if key[0] == tenant_id and key[1] == connection_id:
                del self._records[key]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "fyers-pkce-verifier-cache/v1",
            "backend": "memory",
            "record_count": len(self._records),
        }


class RedisFyersPkceVerifierCache:
    def __init__(
        self,
        *,
        redis_client: Any,
        namespace: str = "portfolio:fyers:pkce",
    ) -> None:
        self._redis_client = redis_client
        self._namespace = namespace.strip(":") or "portfolio:fyers:pkce"

    def store(
        self,
        *,
        session: FyersOAuthSession,
        code_verifier: str,
    ) -> FyersPkceVerifierRecord:
        record = FyersPkceVerifierRecord.create(
            session=session,
            code_verifier=code_verifier,
        )
        ttl_seconds = max(
            int((record.expires_at - record.created_at).total_seconds()),
            1,
        )
        key = self._redis_key(
            tenant_id=record.tenant_id,
            connection_id=record.connection_id,
            state_hash=record.state_hash,
        )
        index_key = self._index_key(
            tenant_id=record.tenant_id,
            connection_id=record.connection_id,
        )
        self._redis_client.setex(key, ttl_seconds, record.code_verifier)
        if hasattr(self._redis_client, "sadd"):
            self._redis_client.sadd(index_key, key)
        if hasattr(self._redis_client, "expire"):
            self._redis_client.expire(index_key, ttl_seconds)
        return record

    def pop(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        state_hash: str,
    ) -> str | None:
        key = self._redis_key(
            tenant_id=tenant_id,
            connection_id=connection_id,
            state_hash=state_hash,
        )
        if hasattr(self._redis_client, "getdel"):
            raw_value = self._redis_client.getdel(key)
        else:
            raw_value = self._redis_client.get(key)
            self._redis_client.delete(key)
        return _decode_redis_value(raw_value)

    def clear_connection(self, *, tenant_id: str, connection_id: str) -> None:
        index_key = self._index_key(tenant_id=tenant_id, connection_id=connection_id)
        keys = set()
        if hasattr(self._redis_client, "smembers"):
            keys = {
                decoded
                for value in self._redis_client.smembers(index_key)
                if (decoded := _decode_redis_value(value))
            }
        if keys:
            self._redis_client.delete(*sorted(keys), index_key)
        else:
            self._redis_client.delete(index_key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "fyers-pkce-verifier-cache/v1",
            "backend": "redis",
            "redis_url": "[REDACTED]",
        }

    def _redis_key(
        self,
        *,
        tenant_id: str,
        connection_id: str,
        state_hash: str,
    ) -> str:
        return f"{self._namespace}:verifier:{tenant_id}:{connection_id}:{state_hash}"

    def _index_key(self, *, tenant_id: str, connection_id: str) -> str:
        return f"{self._namespace}:index:{tenant_id}:{connection_id}"


@dataclass(frozen=True)
class ProviderRefreshJob:
    tenant_id: str
    job_id: str
    provider: str
    requested_by_actor_id: str
    refresh_type: str
    status: str
    source: str
    created_at: datetime
    completed_at: datetime | None
    snapshot_count: int
    error_count: int
    errors: tuple[str, ...]

    @classmethod
    def created(
        cls,
        *,
        tenant_id: str,
        requested_by_actor_id: str,
        refresh_type: str,
        job_id: str | None = None,
        now: datetime | None = None,
    ) -> ProviderRefreshJob:
        timestamp = now or utc_now()
        if job_id is None:
            digest = sha256(
                f"{tenant_id}:{requested_by_actor_id}:{timestamp.isoformat()}".encode(
                    "utf-8"
                )
            ).hexdigest()[:16]
            job_id = f"fyers-refresh-{digest}"
        return cls(
            tenant_id=tenant_id,
            job_id=job_id,
            provider="fyers",
            requested_by_actor_id=requested_by_actor_id,
            refresh_type=refresh_type,
            status="queued",
            source="protected_human_api",
            created_at=timestamp,
            completed_at=None,
            snapshot_count=0,
            error_count=0,
            errors=(),
        )

    def completed(
        self,
        *,
        snapshot_count: int,
        errors: tuple[str, ...] = (),
        now: datetime | None = None,
    ) -> ProviderRefreshJob:
        return replace(
            self,
            status="completed" if not errors else "completed_with_errors",
            completed_at=now or utc_now(),
            snapshot_count=snapshot_count,
            error_count=len(errors),
            errors=errors,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["completed_at"] = (
            self.completed_at.isoformat() if self.completed_at else None
        )
        payload["errors"] = list(self.errors)
        return payload


def hash_oauth_state(state: str) -> str:
    return f"sha256:{sha256(state.encode('utf-8')).hexdigest()}"


def _verifier_key(
    tenant_id: str,
    connection_id: str,
    state_hash: str,
) -> tuple[str, str, str]:
    return (tenant_id, connection_id, state_hash)


def _decode_redis_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)
