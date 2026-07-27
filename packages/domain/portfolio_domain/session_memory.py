from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


class SessionMemoryValidationError(ValueError):
    """Raised when a session-memory payload would violate the privacy contract."""


@dataclass(frozen=True)
class SessionMemoryPolicy:
    idle_ttl: timedelta
    absolute_ttl: timedelta
    max_summary_chars: int
    persist_long_term_preferences: bool
    retain_raw_account_payloads: bool

    @classmethod
    def default(cls) -> SessionMemoryPolicy:
        return cls(
            idle_ttl=timedelta(hours=2),
            absolute_ttl=timedelta(hours=24),
            max_summary_chars=2_000,
            persist_long_term_preferences=False,
            retain_raw_account_payloads=False,
        )


@dataclass(frozen=True)
class SessionMemoryPayload:
    summary: str
    object_refs: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SessionMemoryRecord:
    session_id: str
    tenant_id: str
    actor_identity_id: str
    request_id: str
    summary: str
    object_refs: tuple[dict[str, str], ...]
    idle_expires_at: datetime
    absolute_expires_at: datetime
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "actor_identity_id": self.actor_identity_id,
            "request_id": self.request_id,
            "summary": self.summary,
            "object_refs": [dict(ref) for ref in self.object_refs],
            "idle_expires_at": self.idle_expires_at.isoformat(),
            "absolute_expires_at": self.absolute_expires_at.isoformat(),
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PostgresSessionMemoryStore:
    def __init__(
        self,
        *,
        tenant_id: str,
        actor_identity_id: str,
        connection_factory: Callable[[], Any],
        policy: SessionMemoryPolicy | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required for session memory")
        if not actor_identity_id.strip():
            raise ValueError("actor_identity_id is required for session memory")
        self._tenant_id = tenant_id
        self._actor_identity_id = actor_identity_id
        self._connection_factory = connection_factory
        self._policy = policy or SessionMemoryPolicy.default()
        self._now = now or _utc_now

    def upsert_summary(
        self,
        *,
        session_id: str,
        request_id: str,
        summary: str,
        object_refs: Sequence[Mapping[str, Any]] = (),
    ) -> SessionMemoryRecord:
        if not session_id.strip():
            raise ValueError("session_id is required")
        if not request_id.strip():
            raise ValueError("request_id is required")
        payload = sanitize_session_memory_payload(
            summary=summary,
            object_refs=object_refs,
            policy=self._policy,
        )
        current_time = _aware_utc(self._now())
        params: dict[str, Any] = {
            "session_id": session_id,
            "tenant_id": self._tenant_id,
            "actor_identity_id": self._actor_identity_id,
            "request_id": request_id,
            "summary": payload.summary,
            "object_refs": [dict(ref) for ref in payload.object_refs],
            "idle_expires_at": current_time + self._policy.idle_ttl,
            "absolute_expires_at": current_time + self._policy.absolute_ttl,
            "now": current_time,
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_sessions (
                        id,
                        tenant_id,
                        actor_identity_id,
                        request_id,
                        summary,
                        object_refs,
                        idle_expires_at,
                        absolute_expires_at,
                        deleted_at,
                        created_at,
                        updated_at
                    ) VALUES (
                        %(session_id)s,
                        %(tenant_id)s,
                        %(actor_identity_id)s,
                        %(request_id)s,
                        %(summary)s,
                        %(object_refs)s,
                        %(idle_expires_at)s,
                        %(absolute_expires_at)s,
                        NULL,
                        %(now)s,
                        %(now)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        actor_identity_id = EXCLUDED.actor_identity_id,
                        request_id = EXCLUDED.request_id,
                        summary = EXCLUDED.summary,
                        object_refs = EXCLUDED.object_refs,
                        idle_expires_at = EXCLUDED.idle_expires_at,
                        absolute_expires_at = EXCLUDED.absolute_expires_at,
                        deleted_at = NULL,
                        updated_at = %(now)s
                    WHERE agent_sessions.tenant_id = %(tenant_id)s
                      AND agent_sessions.actor_identity_id = %(actor_identity_id)s
                    RETURNING
                        id,
                        tenant_id,
                        actor_identity_id,
                        request_id,
                        summary,
                        object_refs,
                        idle_expires_at,
                        absolute_expires_at,
                        deleted_at,
                        created_at,
                        updated_at
                    """.strip(),
                    params,
                )
                row = _cursor_one(cursor)
            connection.commit()
        if row is None:
            raise ValueError("Session memory upsert failed tenant scope check")
        return _row_to_session_memory_record(row)

    def get(self, session_id: str) -> SessionMemoryRecord | None:
        if not session_id.strip():
            raise ValueError("session_id is required")
        current_time = _aware_utc(self._now())
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        tenant_id,
                        actor_identity_id,
                        request_id,
                        summary,
                        object_refs,
                        idle_expires_at,
                        absolute_expires_at,
                        deleted_at,
                        created_at,
                        updated_at
                    FROM agent_sessions
                    WHERE id = %(session_id)s
                      AND tenant_id = %(tenant_id)s
                      AND actor_identity_id = %(actor_identity_id)s
                      AND deleted_at IS NULL
                      AND idle_expires_at > %(now)s
                      AND absolute_expires_at > %(now)s
                    """.strip(),
                    {
                        "session_id": session_id,
                        "tenant_id": self._tenant_id,
                        "actor_identity_id": self._actor_identity_id,
                        "now": current_time,
                    },
                )
                row = _cursor_one(cursor)
        return _row_to_session_memory_record(row) if row is not None else None

    def delete(self, session_id: str) -> None:
        if not session_id.strip():
            raise ValueError("session_id is required")
        current_time = _aware_utc(self._now())
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE agent_sessions
                    SET deleted_at = %(now)s,
                        updated_at = %(now)s
                    WHERE id = %(session_id)s
                      AND tenant_id = %(tenant_id)s
                      AND actor_identity_id = %(actor_identity_id)s
                    """.strip(),
                    {
                        "session_id": session_id,
                        "tenant_id": self._tenant_id,
                        "actor_identity_id": self._actor_identity_id,
                        "now": current_time,
                    },
                )
            connection.commit()


def sanitize_session_memory_payload(
    *,
    summary: str,
    object_refs: Sequence[Mapping[str, Any]],
    policy: SessionMemoryPolicy | None = None,
) -> SessionMemoryPayload:
    active_policy = policy or SessionMemoryPolicy.default()
    normalized_summary = " ".join(summary.strip().split())
    if not normalized_summary:
        raise SessionMemoryValidationError("Session summary must not be empty")
    if len(normalized_summary) > active_policy.max_summary_chars:
        raise SessionMemoryValidationError("Session summary exceeds the compact memory limit")
    if _contains_forbidden_summary_content(normalized_summary, active_policy):
        raise SessionMemoryValidationError(
            "Session summaries may contain compact task context only, not secrets, raw account data, private notes, or long-term preferences"
        )
    return SessionMemoryPayload(
        summary=normalized_summary,
        object_refs=tuple(_sanitize_object_ref(ref) for ref in object_refs),
    )


def _contains_forbidden_summary_content(
    summary: str,
    policy: SessionMemoryPolicy,
) -> bool:
    lowered = summary.lower()
    forbidden_fragments = [
        "access_token",
        "refresh_token",
        "api_key",
        "authorization:",
        "bearer ",
        "credential",
        "password",
        "secret",
        "fyers token",
        "fyers_token",
        "broker token",
        "raw account payload",
        "raw_account_payload",
        "private note",
        "personal note",
    ]
    if not policy.persist_long_term_preferences:
        forbidden_fragments.extend(
            [
                "remember my",
                "long-term preference",
                "long term preference",
                "retain my preference",
                "store my preference",
            ]
        )
    if not policy.retain_raw_account_payloads:
        forbidden_fragments.extend(
            [
                "'holdings'",
                '"holdings"',
                "'funds'",
                '"funds"',
                "'positions'",
                '"positions"',
            ]
        )
    return any(fragment in lowered for fragment in forbidden_fragments)


def _sanitize_object_ref(ref: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(ref, Mapping):
        raise SessionMemoryValidationError("Session object references must be mappings")
    blocked_key_fragments = (
        "credential",
        "password",
        "secret",
        "token",
        "payload",
        "raw",
        "path",
        "resolved",
    )
    for key in ref:
        if any(fragment in str(key).lower() for fragment in blocked_key_fragments):
            raise SessionMemoryValidationError("Session object references may not include raw data or secrets")
    allowed_keys = ("type", "id", "version", "checksum", "as_of")
    clean_ref: dict[str, str] = {}
    for key in allowed_keys:
        value = ref.get(key)
        if value is None:
            continue
        clean_value = str(value).strip()
        if not clean_value:
            continue
        if _contains_forbidden_ref_value(clean_value):
            raise SessionMemoryValidationError("Session object references may not include raw data or secrets")
        clean_ref[key] = clean_value
    if not clean_ref.get("type") or not clean_ref.get("id"):
        raise SessionMemoryValidationError("Session object references require type and id")
    return clean_ref


def _contains_forbidden_ref_value(value: str) -> bool:
    lowered = value.lower()
    return any(
        fragment in lowered
        for fragment in (
            "access_token",
            "refresh_token",
            "api_key",
            "password",
            "secret",
            "bearer ",
            "{",
            "}",
        )
    )


def _cursor_one(cursor: Any) -> dict[str, Any] | None:
    row = cursor.fetchone()
    if row is None:
        return None
    return _row_mapping(cursor, row)


def _row_mapping(cursor: Any, row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    if not isinstance(row, Sequence):
        raise TypeError("Postgres session memory rows must be mappings or sequences")
    description = getattr(cursor, "description", None)
    if not description:
        raise TypeError("Postgres session memory sequence rows require description")
    keys = [str(column[0]) for column in description]
    return dict(zip(keys, row, strict=False))


def _row_to_session_memory_record(row: Mapping[str, Any]) -> SessionMemoryRecord:
    return SessionMemoryRecord(
        session_id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        actor_identity_id=str(row["actor_identity_id"]),
        request_id=str(row["request_id"]),
        summary=str(row["summary"]),
        object_refs=tuple(_sanitize_object_ref(ref) for ref in _object_refs(row.get("object_refs"))),
        idle_expires_at=_datetime_value(row["idle_expires_at"]),
        absolute_expires_at=_datetime_value(row["absolute_expires_at"]),
        deleted_at=_optional_datetime_value(row.get("deleted_at")),
        created_at=_datetime_value(row["created_at"]),
        updated_at=_datetime_value(row["updated_at"]),
    )


def _object_refs(value: Any) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _datetime_value(value: Any) -> datetime:
    if isinstance(value, datetime):
        return _aware_utc(value)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _aware_utc(parsed)
    raise TypeError("Session memory timestamp must be a datetime or ISO timestamp")


def _optional_datetime_value(value: Any) -> datetime | None:
    if value is None:
        return None
    return _datetime_value(value)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
