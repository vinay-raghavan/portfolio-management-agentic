from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .database_runtime import DatabaseBackend
from .paper_execution_queue_processor import PaperExecutionQueueProcessor
from .paper_execution_store import PostgresPaperExecutionStore


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


def _psycopg_database_url(database_url: str) -> str:
    stripped = database_url.strip()
    if stripped.startswith("postgresql+psycopg://"):
        return "postgresql://" + stripped.removeprefix("postgresql+psycopg://")
    return stripped

