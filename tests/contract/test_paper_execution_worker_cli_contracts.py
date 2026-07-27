from __future__ import annotations

from scripts.process_paper_execution_queue import (
    build_schedule_state,
    parse_tenant_ids,
)


def test_worker_cli_parses_unique_comma_separated_tenant_ids() -> None:
    assert parse_tenant_ids(" tenant-a, tenant-b,,tenant-a ") == (
        "tenant-a",
        "tenant-b",
    )


def test_worker_cli_falls_back_to_single_tenant_id() -> None:
    assert parse_tenant_ids("", fallback_tenant_id=" tenant-single ") == (
        "tenant-single",
    )


class _FakeRedisModule:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def from_url(self, redis_url: str):
        self.urls.append(redis_url)
        return {"redis_url": redis_url}


def test_worker_cli_builds_redis_schedule_state_without_exposing_url() -> None:
    fake_redis = _FakeRedisModule()

    state = build_schedule_state(
        redis_url="redis://:redis-secret@redis:6379/0",
        worker_id="paper-worker",
        redis_factory=fake_redis.from_url,
    )

    assert state is not None
    assert fake_redis.urls == ["redis://:redis-secret@redis:6379/0"]
    assert state.key_prefix == "portfolio:paper-execution-worker:paper-worker"
    assert "redis-secret" not in str(state.to_dict())


def test_worker_cli_skips_schedule_state_when_redis_url_missing() -> None:
    assert build_schedule_state(redis_url="", worker_id="paper-worker") is None
