from __future__ import annotations

import json
from types import SimpleNamespace

import scripts.process_paper_execution_queue as worker_cli
from scripts.process_paper_execution_queue import (
    build_schedule_state,
    build_worker_ids,
    env_flag_enabled,
    main,
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


def test_worker_cli_builds_stable_tenant_worker_ids() -> None:
    assert build_worker_ids(
        ("tenant-a", "tenant-b"),
        worker_id="paper-worker",
    ) == ("paper-worker:tenant-a", "paper-worker:tenant-b")


def test_worker_cli_reads_operator_kill_switch_env(monkeypatch) -> None:
    assert env_flag_enabled(
        "PAPER_EXECUTION_KILL_SWITCH",
        "PORTFOLIO_PAPER_EXECUTION_KILL_SWITCH",
    ) is False

    monkeypatch.setenv("PORTFOLIO_PAPER_EXECUTION_KILL_SWITCH", "true")

    assert env_flag_enabled(
        "PAPER_EXECUTION_KILL_SWITCH",
        "PORTFOLIO_PAPER_EXECUTION_KILL_SWITCH",
    ) is True


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


class _FakeScheduleState:
    def to_dict(self):
        return {
            "schema_version": "paper-execution-fake-schedule-state/v1",
            "backend": "fake",
        }

    def order_worker_ids(self, worker_ids):
        return worker_ids

    def worker_is_backed_off(self, worker_id, *, now):
        return worker_id.endswith("tenant-b")

    def mark_worker_result(self, *, worker_id, status, now):
        raise AssertionError("health snapshots must not mutate schedule state")


def test_worker_cli_health_snapshot_does_not_process_queue_or_expose_redis_url(
    monkeypatch,
    capsys,
) -> None:
    def fake_build_schedule_state(*, redis_url, worker_id, backoff_seconds=30):
        assert redis_url == "redis://:redis-secret@redis:6379/0"
        assert worker_id == "paper-worker"
        assert backoff_seconds == 30
        return _FakeScheduleState()

    def forbidden_build_worker(**kwargs):
        raise AssertionError("health snapshots must not build or process workers")

    monkeypatch.setattr(worker_cli, "build_schedule_state", fake_build_schedule_state)
    monkeypatch.setattr(
        worker_cli,
        "build_postgres_paper_execution_fair_worker",
        forbidden_build_worker,
    )

    exit_code = main(
        [
            "--health",
            "--tenant-ids",
            "tenant-a,tenant-b",
            "--worker-id",
            "paper-worker",
            "--redis-url",
            "redis://:redis-secret@redis:6379/0",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "paper-execution-worker-health/v1"
    assert payload["worker_ids"] == ["paper-worker:tenant-a", "paper-worker:tenant-b"]
    assert payload["per_worker"] == [
        {"worker_id": "paper-worker:tenant-a", "backed_off": False},
        {"worker_id": "paper-worker:tenant-b", "backed_off": True},
    ]
    assert payload["model_visible"] is False
    assert "redis-secret" not in str(payload)
    assert "redis://" not in str(payload)


def test_worker_cli_passes_operator_kill_switch_to_fair_runner(
    monkeypatch,
    capsys,
) -> None:
    captured: dict[str, object] = {}

    class _FakeSummary:
        idle = True

        def to_dict(self):
            return {
                "schema_version": "paper-execution-worker-runner-summary/v1",
                "processed": 0,
                "failed": 1,
                "idle": True,
                "total_attempted": 1,
            }

    class _FakeRunner:
        def run_until_idle(self, *, max_items: int):
            captured["max_items"] = max_items
            return _FakeSummary()

    def fake_build_fair_worker(**kwargs):
        captured.update(kwargs)
        return _FakeRunner()

    monkeypatch.setenv("PORTFOLIO_PAPER_EXECUTION_KILL_SWITCH", "true")
    monkeypatch.setattr(worker_cli, "build_schedule_state", lambda **kwargs: None)
    monkeypatch.setattr(
        worker_cli,
        "load_database_runtime_profile",
        lambda env: SimpleNamespace(database_url="postgresql://db", backend="postgres"),
    )
    monkeypatch.setattr(
        worker_cli,
        "build_postgres_paper_execution_fair_worker",
        fake_build_fair_worker,
    )

    exit_code = main(
        [
            "--tenant-id",
            "tenant-a",
            "--worker-id",
            "paper-worker",
            "--max-items",
            "7",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["failed"] == 1
    assert captured["tenant_ids"] == ("tenant-a",)
    assert captured["worker_id"] == "paper-worker"
    assert captured["kill_switch_active"] is True
    assert captured["max_items"] == 7
