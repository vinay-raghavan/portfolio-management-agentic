from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class ActorIdentityRecord:
    actor_identity_id: str
    issuer: str
    subject: str
    email_hash: str | None
    display_name: str | None
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["last_seen_at"] = self.last_seen_at.isoformat()
        payload["created_at"] = self.created_at.isoformat()
        payload["updated_at"] = self.updated_at.isoformat()
        return payload


class PostgresActorIdentityStore:
    """Resolve verified issuer/subject pairs into stable Postgres identity IDs."""

    def __init__(
        self,
        *,
        connection_factory: Callable[[], Any],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._now = now or (lambda: datetime.now(UTC))

    def upsert_identity(
        self,
        *,
        issuer: str,
        subject: str,
        email_hash: str | None = None,
        display_name: str | None = None,
    ) -> ActorIdentityRecord:
        normalized_issuer = issuer.strip()
        normalized_subject = subject.strip()
        if not normalized_issuer:
            raise ValueError("issuer is required for actor identity")
        if not normalized_subject:
            raise ValueError("subject is required for actor identity")
        current_time = _aware_utc(self._now())
        params = {
            "issuer": normalized_issuer,
            "subject": normalized_subject,
            "email_hash": _blank_to_none(email_hash),
            "display_name": _blank_to_none(display_name),
            "now": current_time,
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO actor_identities (
                        issuer,
                        subject,
                        email_hash,
                        display_name,
                        last_seen_at,
                        created_at,
                        updated_at
                    ) VALUES (
                        %(issuer)s,
                        %(subject)s,
                        %(email_hash)s,
                        %(display_name)s,
                        %(now)s,
                        %(now)s,
                        %(now)s
                    )
                    ON CONFLICT (issuer, subject) DO UPDATE SET
                        email_hash = COALESCE(EXCLUDED.email_hash, actor_identities.email_hash),
                        display_name = COALESCE(EXCLUDED.display_name, actor_identities.display_name),
                        last_seen_at = EXCLUDED.last_seen_at,
                        updated_at = EXCLUDED.updated_at
                    RETURNING
                        id,
                        issuer,
                        subject,
                        email_hash,
                        display_name,
                        last_seen_at,
                        created_at,
                        updated_at
                    """.strip(),
                    params,
                )
                row = _cursor_one(cursor)
            connection.commit()
        if row is None:
            raise RuntimeError("Actor identity upsert did not return a row")
        return _row_to_actor_identity(row)


def _cursor_one(cursor: Any) -> dict[str, Any] | None:
    row = cursor.fetchone()
    if row is None:
        return None
    return _row_mapping(cursor, row)


def _row_mapping(cursor: Any, row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    if not isinstance(row, Sequence) or isinstance(row, (str, bytes, bytearray)):
        raise TypeError("Postgres actor identity rows must be mappings or sequences")
    description = getattr(cursor, "description", None)
    if not description:
        raise TypeError("Postgres actor identity sequence rows require description")
    keys = [str(column[0]) for column in description]
    return dict(zip(keys, row, strict=False))


def _row_to_actor_identity(row: Mapping[str, Any]) -> ActorIdentityRecord:
    return ActorIdentityRecord(
        actor_identity_id=str(row["id"]),
        issuer=str(row["issuer"]),
        subject=str(row["subject"]),
        email_hash=_blank_to_none(row.get("email_hash")),
        display_name=_blank_to_none(row.get("display_name")),
        last_seen_at=_datetime_value(row["last_seen_at"]),
        created_at=_datetime_value(row["created_at"]),
        updated_at=_datetime_value(row["updated_at"]),
    )


def _datetime_value(value: Any) -> datetime:
    if isinstance(value, datetime):
        return _aware_utc(value)
    if isinstance(value, str):
        return _aware_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    raise TypeError("Actor identity timestamp must be a datetime or ISO timestamp")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _blank_to_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
