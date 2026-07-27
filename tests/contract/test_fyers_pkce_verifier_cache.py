from __future__ import annotations

from datetime import datetime, timedelta, timezone

from portfolio_domain import (
    FyersOAuthSession,
    FyersPkceVerifierRecord,
    InMemoryFyersPkceVerifierCache,
    RedisFyersPkceVerifierCache,
    hash_oauth_state,
)


NOW = datetime(2026, 7, 27, 9, 45, tzinfo=timezone.utc)
TENANT_ID = "tenant-pkce"
CONNECTION_ID = "connection-pkce"
STATE = "browser-state"
STATE_HASH = hash_oauth_state(STATE)
VERIFIER = "super-secret-pkce-code-verifier"


class _FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.setex_calls: list[tuple[str, int, str]] = []
        self.sadd_calls: list[tuple[str, str]] = []
        self.expire_calls: list[tuple[str, int]] = []
        self.deleted: list[tuple[str, ...]] = []

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.values[key] = value
        self.setex_calls.append((key, ttl_seconds, value))

    def getdel(self, key: str) -> str | None:
        return self.values.pop(key, None)

    def sadd(self, key: str, value: str) -> None:
        self.sadd_calls.append((key, value))

    def expire(self, key: str, ttl_seconds: int) -> None:
        self.expire_calls.append((key, ttl_seconds))

    def smembers(self, key: str) -> set[str]:
        return {value for index_key, value in self.sadd_calls if index_key == key}

    def delete(self, *keys: str) -> None:
        self.deleted.append(tuple(keys))
        for key in keys:
            self.values.pop(key, None)


def _session(ttl: timedelta = timedelta(minutes=10)) -> FyersOAuthSession:
    return FyersOAuthSession.create(
        tenant_id=TENANT_ID,
        connection_id=CONNECTION_ID,
        state=STATE,
        code_challenge="pkce-challenge",
        now=NOW,
        ttl=ttl,
    )


def test_pkce_verifier_record_is_redacted_and_scoped() -> None:
    record = FyersPkceVerifierRecord.create(
        session=_session(),
        code_verifier=VERIFIER,
    )

    assert record.tenant_id == TENANT_ID
    assert record.connection_id == CONNECTION_ID
    assert record.state_hash == STATE_HASH
    assert record.code_verifier == VERIFIER
    assert record.to_dict()["code_verifier_configured"] is True
    serialized = f"{record!r} {record.to_dict()}".lower()
    assert VERIFIER not in serialized
    assert "code_verifier" in serialized
    assert "super-secret" not in serialized


def test_in_memory_pkce_verifier_cache_pops_once_and_expires() -> None:
    cache = InMemoryFyersPkceVerifierCache(now=lambda: NOW)
    session = _session()

    stored = cache.store(session=session, code_verifier=VERIFIER)
    first = cache.pop(
        tenant_id=TENANT_ID,
        connection_id=CONNECTION_ID,
        state_hash=STATE_HASH,
    )
    second = cache.pop(
        tenant_id=TENANT_ID,
        connection_id=CONNECTION_ID,
        state_hash=STATE_HASH,
    )
    cache.store(
        session=_session(ttl=timedelta(seconds=-1)),
        code_verifier="expired-verifier",
    )
    expired = cache.pop(
        tenant_id=TENANT_ID,
        connection_id=CONNECTION_ID,
        state_hash=STATE_HASH,
    )

    assert stored.code_verifier == VERIFIER
    assert first == VERIFIER
    assert second is None
    assert expired is None
    assert VERIFIER not in str(cache.to_dict())


def test_in_memory_pkce_verifier_cache_clears_connection_scope() -> None:
    cache = InMemoryFyersPkceVerifierCache(now=lambda: NOW)
    session = _session()
    cache.store(session=session, code_verifier=VERIFIER)

    cache.clear_connection(tenant_id=TENANT_ID, connection_id=CONNECTION_ID)
    popped = cache.pop(
        tenant_id=TENANT_ID,
        connection_id=CONNECTION_ID,
        state_hash=STATE_HASH,
    )

    assert popped is None


def test_redis_pkce_verifier_cache_uses_ttl_and_redacted_keys() -> None:
    client = _FakeRedisClient()
    cache = RedisFyersPkceVerifierCache(redis_client=client, namespace="test:fyers:pkce")
    session = _session()

    cache.store(session=session, code_verifier=VERIFIER)
    popped = cache.pop(
        tenant_id=TENANT_ID,
        connection_id=CONNECTION_ID,
        state_hash=STATE_HASH,
    )

    key, ttl_seconds, value = client.setex_calls[0]
    assert popped == VERIFIER
    assert ttl_seconds == 600
    assert value == VERIFIER
    assert "super-secret" not in key
    assert "code_verifier" not in key
    assert client.sadd_calls
    assert client.expire_calls[0][1] == 600
    assert cache.to_dict() == {
        "schema_version": "fyers-pkce-verifier-cache/v1",
        "backend": "redis",
        "redis_url": "[REDACTED]",
    }


def test_redis_pkce_verifier_cache_clears_indexed_connection_keys() -> None:
    client = _FakeRedisClient()
    cache = RedisFyersPkceVerifierCache(redis_client=client, namespace="test:fyers:pkce")
    cache.store(session=_session(), code_verifier=VERIFIER)

    cache.clear_connection(tenant_id=TENANT_ID, connection_id=CONNECTION_ID)

    assert client.deleted
    deleted_keys = {key for call in client.deleted for key in call}
    assert any("tenant-pkce" in key for key in deleted_keys)
    assert VERIFIER not in str(deleted_keys)
