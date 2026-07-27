from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol

from .database_runtime import DatabaseBackend
from .paper_execution_queue_processor import (
    PaperExecutionQueueProcessor,
    PaperExecutionQueueProcessorResult,
)
from .paper_execution_store import PostgresPaperExecutionStore


class PaperExecutionProcessor(Protocol):
    worker_id: str

    def process_once(
        self,
        *,
        work_item_id: str | None = None,
    ) -> PaperExecutionQueueProcessorResult: ...


class PaperExecutionWorkerScheduleState(Protocol):
    def order_worker_ids(self, worker_ids: tuple[str, ...]) -> tuple[str, ...]: ...

    def worker_is_backed_off(self, worker_id: str, *, now: datetime) -> bool: ...

    def mark_worker_result(
        self,
        *,
        worker_id: str,
        status: str,
        now: datetime,
    ) -> None: ...


@dataclass(frozen=True)
class PaperExecutionRedisScheduleState:
    """Redis-backed worker scheduling cursor and short-lived failure backoff."""

    redis_client: Any
    key_prefix: str = "portfolio:paper-execution-worker"
    backoff_seconds: int = 30
    now: Callable[[], datetime] | None = None

    def order_worker_ids(self, worker_ids: tuple[str, ...]) -> tuple[str, ...]:
        clean_worker_ids = tuple(worker_id for worker_id in worker_ids if worker_id)
        if not clean_worker_ids:
            return ()
        last_worker_id = _decode_redis_value(
            self.redis_client.get(self._key("cursor"))
        )
        if last_worker_id not in clean_worker_ids:
            return clean_worker_ids
        cursor_index = clean_worker_ids.index(last_worker_id)
        return clean_worker_ids[cursor_index + 1 :] + clean_worker_ids[: cursor_index + 1]

    def worker_is_backed_off(self, worker_id: str, *, now: datetime) -> bool:
        raw_value = _decode_redis_value(
            self.redis_client.get(self._key("backoff", worker_id))
        )
        if raw_value is None:
            return False
        try:
            backoff_until = _aware_utc(datetime.fromisoformat(raw_value))
        except ValueError:
            return False
        return backoff_until > _aware_utc(now)

    def mark_worker_result(
        self,
        *,
        worker_id: str,
        status: str,
        now: datetime,
    ) -> None:
        clean_worker_id = worker_id.strip()
        if not clean_worker_id:
            return
        self.redis_client.set(self._key("cursor"), clean_worker_id)
        if status != "failed":
            return
        seconds = max(int(self.backoff_seconds), 1)
        backoff_until = _aware_utc(now) + timedelta(seconds=seconds)
        self.redis_client.setex(
            self._key("backoff", clean_worker_id),
            seconds,
            backoff_until.isoformat(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "paper-execution-redis-schedule-state/v1",
            "key_prefix": self.key_prefix,
            "backoff_seconds": self.backoff_seconds,
            "backend": "redis",
        }

    def _key(self, *parts: str) -> str:
        clean_prefix = self.key_prefix.strip().strip(":")
        clean_parts = [part.strip().replace(":", "_") for part in parts if part.strip()]
        return ":".join((clean_prefix, *clean_parts))


@dataclass(frozen=True)
class PaperExecutionQueueRunnerSummary:
    processed: int
    failed: int
    idle: bool
    total_attempted: int
    worker_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "paper-execution-worker-runner-summary/v1",
            "processed": self.processed,
            "failed": self.failed,
            "idle": self.idle,
            "total_attempted": self.total_attempted,
            "worker_id": self.worker_id,
        }


@dataclass(frozen=True)
class PaperExecutionFairQueueRunnerWorkerSummary:
    worker_id: str
    processed: int
    failed: int
    idle: bool
    total_attempted: int

    def to_dict(self) -> dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "processed": self.processed,
            "failed": self.failed,
            "idle": self.idle,
            "total_attempted": self.total_attempted,
        }


@dataclass(frozen=True)
class PaperExecutionFairQueueRunnerSummary:
    processed: int
    failed: int
    idle: bool
    total_attempted: int
    per_worker: tuple[PaperExecutionFairQueueRunnerWorkerSummary, ...]

    @property
    def worker_ids(self) -> tuple[str, ...]:
        return tuple(worker.worker_id for worker in self.per_worker)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "paper-execution-fair-worker-runner-summary/v1",
            "processed": self.processed,
            "failed": self.failed,
            "idle": self.idle,
            "total_attempted": self.total_attempted,
            "worker_ids": list(self.worker_ids),
            "per_worker": [worker.to_dict() for worker in self.per_worker],
        }


@dataclass(frozen=True)
class PaperExecutionQueueRunner:
    """Standalone paper-only worker loop around the queue processor."""

    processor: PaperExecutionQueueProcessor

    def run_until_idle(
        self,
        *,
        max_items: int,
    ) -> PaperExecutionQueueRunnerSummary:
        if max_items <= 0:
            raise ValueError("max_items must be positive")

        processed = 0
        failed = 0
        idle = False

        for _ in range(max_items):
            result = self.processor.process_once()
            if result.status == "no_work":
                idle = True
                break
            if result.status == "processed":
                processed += 1
                continue
            failed += 1

        return PaperExecutionQueueRunnerSummary(
            processed=processed,
            failed=failed,
            idle=idle,
            total_attempted=processed + failed,
            worker_id=self.processor.worker_id,
        )


@dataclass(frozen=True)
class PaperExecutionFairQueueRunner:
    """Round-robin paper-only queue processing across tenant-scoped processors."""

    processors: tuple[PaperExecutionProcessor, ...]
    schedule_state: PaperExecutionWorkerScheduleState | None = None
    now: Callable[[], datetime] | None = None

    def __post_init__(self) -> None:
        if not self.processors:
            raise ValueError("at_least_one_processor_required")

    def run_until_idle(
        self,
        *,
        max_items: int,
    ) -> PaperExecutionFairQueueRunnerSummary:
        if max_items <= 0:
            raise ValueError("max_items must be positive")

        processed_by_worker = {processor.worker_id: 0 for processor in self.processors}
        failed_by_worker = {processor.worker_id: 0 for processor in self.processors}
        idle_by_worker = {processor.worker_id: False for processor in self.processors}
        total_attempted = 0
        processors_by_id = {processor.worker_id: processor for processor in self.processors}

        while total_attempted < max_items and not all(idle_by_worker.values()):
            made_attempt = False
            ordered_worker_ids = self._ordered_worker_ids()
            for worker_id in ordered_worker_ids:
                if total_attempted >= max_items:
                    break
                if idle_by_worker[worker_id]:
                    continue
                if self._worker_is_backed_off(worker_id):
                    idle_by_worker[worker_id] = True
                    continue
                processor = processors_by_id[worker_id]
                result = processor.process_once()
                if result.status == "no_work":
                    idle_by_worker[worker_id] = True
                    continue
                made_attempt = True
                total_attempted += 1
                self._mark_worker_result(worker_id=worker_id, status=result.status)
                if result.status == "processed":
                    processed_by_worker[worker_id] += 1
                else:
                    failed_by_worker[worker_id] += 1
            if not made_attempt and all(idle_by_worker.values()):
                break

        per_worker = tuple(
            PaperExecutionFairQueueRunnerWorkerSummary(
                worker_id=processor.worker_id,
                processed=processed_by_worker[processor.worker_id],
                failed=failed_by_worker[processor.worker_id],
                idle=idle_by_worker[processor.worker_id],
                total_attempted=(
                    processed_by_worker[processor.worker_id]
                    + failed_by_worker[processor.worker_id]
                ),
            )
            for processor in self.processors
        )
        return PaperExecutionFairQueueRunnerSummary(
            processed=sum(processed_by_worker.values()),
            failed=sum(failed_by_worker.values()),
            idle=all(idle_by_worker.values()),
            total_attempted=total_attempted,
            per_worker=per_worker,
        )

    def _ordered_worker_ids(self) -> tuple[str, ...]:
        worker_ids = tuple(processor.worker_id for processor in self.processors)
        if self.schedule_state is None:
            return worker_ids
        ordered = self.schedule_state.order_worker_ids(worker_ids)
        return ordered or worker_ids

    def _worker_is_backed_off(self, worker_id: str) -> bool:
        if self.schedule_state is None:
            return False
        return self.schedule_state.worker_is_backed_off(
            worker_id,
            now=self._current_time(),
        )

    def _mark_worker_result(self, *, worker_id: str, status: str) -> None:
        if self.schedule_state is None:
            return
        self.schedule_state.mark_worker_result(
            worker_id=worker_id,
            status=status,
            now=self._current_time(),
        )

    def _current_time(self) -> datetime:
        return _aware_utc(self.now() if self.now is not None else _utc_now())


def build_postgres_paper_execution_worker(
    *,
    tenant_id: str,
    database_url: str | None,
    backend: DatabaseBackend,
    worker_id: str = "paper-execution-worker",
    now: Callable[[], datetime] | None = None,
) -> PaperExecutionQueueRunner:
    """Build the production-like queued paper execution worker.

    The worker is intentionally Postgres-only because durable queue processing
    requires the tenant-scoped queue and ledger tables. SQLite remains a local
    API fallback, not a production worker backend.
    """

    if backend != DatabaseBackend.POSTGRES:
        raise ValueError("postgres_storage_required")
    if database_url is None or not database_url.strip():
        raise ValueError("postgres_database_url_required")

    connection_url = _psycopg_database_url(database_url)

    def connection_factory():
        import psycopg

        return psycopg.connect(connection_url)

    store = PostgresPaperExecutionStore(
        tenant_id=tenant_id,
        connection_factory=connection_factory,
        now=now,
    )
    return PaperExecutionQueueRunner(
        processor=PaperExecutionQueueProcessor(
            store=store,
            worker_id=worker_id,
            now=now,
        )
    )


def build_postgres_paper_execution_fair_worker(
    *,
    tenant_ids: tuple[str, ...],
    database_url: str | None,
    backend: DatabaseBackend,
    worker_id: str = "paper-execution-worker",
    now: Callable[[], datetime] | None = None,
    schedule_state: PaperExecutionWorkerScheduleState | None = None,
) -> PaperExecutionFairQueueRunner:
    clean_tenant_ids = _clean_tenant_ids(tenant_ids)
    if not clean_tenant_ids:
        raise ValueError("tenant_id_required")
    return PaperExecutionFairQueueRunner(
        schedule_state=schedule_state,
        now=now,
        processors=tuple(
            build_postgres_paper_execution_worker(
                tenant_id=tenant_id,
                database_url=database_url,
                backend=backend,
                worker_id=f"{worker_id}:{tenant_id}",
                now=now,
            ).processor
            for tenant_id in clean_tenant_ids
        )
    )


def _clean_tenant_ids(tenant_ids: tuple[str, ...]) -> tuple[str, ...]:
    clean: list[str] = []
    seen: set[str] = set()
    for tenant_id in tenant_ids:
        stripped = tenant_id.strip()
        if not stripped or stripped in seen:
            continue
        clean.append(stripped)
        seen.add(stripped)
    return tuple(clean)


def _psycopg_database_url(database_url: str) -> str:
    stripped = database_url.strip()
    if stripped.startswith("postgresql+psycopg://"):
        return "postgresql://" + stripped.removeprefix("postgresql+psycopg://")
    return stripped


def _decode_redis_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
