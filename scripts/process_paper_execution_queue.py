from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_PATH = REPO_ROOT / "packages" / "domain"
if str(DOMAIN_PATH) not in sys.path:
    sys.path.insert(0, str(DOMAIN_PATH))

from portfolio_domain import (  # noqa: E402
    PaperExecutionRedisScheduleState,
    PaperExecutionWorkerHealthSnapshot,
    build_postgres_paper_execution_fair_worker,
    load_database_runtime_profile,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Process queued paper-only execution work items through the "
            "deterministic Postgres worker boundary."
        )
    )
    parser.add_argument(
        "--tenant-id",
        default=os.environ.get("PORTFOLIO_TENANT_ID", ""),
        help=(
            "Single tenant UUID fallback. Defaults to PORTFOLIO_TENANT_ID and "
            "is ignored when --tenant-ids or PORTFOLIO_TENANT_IDS are set."
        ),
    )
    parser.add_argument(
        "--tenant-ids",
        default=os.environ.get("PORTFOLIO_TENANT_IDS", ""),
        help=(
            "Comma-separated tenant UUIDs to process in round-robin order. "
            "Defaults to PORTFOLIO_TENANT_IDS."
        ),
    )
    parser.add_argument(
        "--worker-id",
        default=os.environ.get(
            "PAPER_EXECUTION_WORKER_ID",
            "paper-execution-worker",
        ),
        help="Stable worker identifier recorded on claimed queue rows.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=int(os.environ.get("PAPER_EXECUTION_WORKER_MAX_ITEMS", "100")),
        help="Maximum items to process per polling cycle.",
    )
    parser.add_argument(
        "--idle-sleep-seconds",
        type=float,
        default=float(os.environ.get("PAPER_EXECUTION_WORKER_IDLE_SLEEP_SECONDS", "5")),
        help="Sleep duration between idle daemon polling cycles.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Continue polling after idle cycles. Default exits after one idle cycle.",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help=(
            "Print a read-only worker health/backoff snapshot and exit without "
            "claiming or processing queue items."
        ),
    )
    parser.add_argument(
        "--redis-url",
        default=os.environ.get("REDIS_URL", ""),
        help="Redis URL for distributed worker schedule/backoff state.",
    )
    parser.add_argument(
        "--schedule-backoff-seconds",
        type=int,
        default=int(
            os.environ.get("PAPER_EXECUTION_WORKER_SCHEDULE_BACKOFF_SECONDS", "30")
        ),
        help="Short Redis backoff duration after a tenant-scoped worker failure.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    tenant_ids = parse_tenant_ids(args.tenant_ids, fallback_tenant_id=args.tenant_id)
    if args.max_items <= 0:
        print(
            json.dumps(
                {
                    "status": "error",
                    "reason": "max_items_must_be_positive",
                },
                sort_keys=True,
            )
        )
        return 2
    if not tenant_ids:
        print(
            json.dumps(
                {
                    "reason": "tenant_id_required",
                    "status": "error",
                },
                sort_keys=True,
            )
        )
        return 2

    schedule_state = build_schedule_state(
        redis_url=args.redis_url,
        worker_id=args.worker_id,
        backoff_seconds=args.schedule_backoff_seconds,
    )
    if args.health:
        health = PaperExecutionWorkerHealthSnapshot.from_worker_ids(
            worker_ids=build_worker_ids(tenant_ids, worker_id=args.worker_id),
            schedule_state=schedule_state,
        )
        print(json.dumps(health.to_dict(), sort_keys=True))
        return 0

    profile = load_database_runtime_profile(os.environ)
    runner = build_postgres_paper_execution_fair_worker(
        tenant_ids=tenant_ids,
        database_url=profile.database_url,
        backend=profile.backend,
        worker_id=args.worker_id,
        schedule_state=schedule_state,
    )

    while True:
        summary = runner.run_until_idle(max_items=args.max_items)
        print(json.dumps(summary.to_dict(), sort_keys=True))
        if not args.daemon:
            return 0
        if summary.idle:
            time.sleep(max(args.idle_sleep_seconds, 0.0))


def parse_tenant_ids(
    raw_tenant_ids: str,
    *,
    fallback_tenant_id: str = "",
) -> tuple[str, ...]:
    raw_values = raw_tenant_ids.split(",") if raw_tenant_ids.strip() else []
    if not raw_values and fallback_tenant_id.strip():
        raw_values = [fallback_tenant_id]
    clean: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        tenant_id = raw_value.strip()
        if not tenant_id or tenant_id in seen:
            continue
        clean.append(tenant_id)
        seen.add(tenant_id)
    return tuple(clean)


def build_worker_ids(
    tenant_ids: tuple[str, ...],
    *,
    worker_id: str,
) -> tuple[str, ...]:
    clean_worker_id = worker_id.strip() or "paper-execution-worker"
    return tuple(
        f"{clean_worker_id}:{tenant_id}"
        for tenant_id in parse_tenant_ids(",".join(tenant_ids))
    )


def build_schedule_state(
    *,
    redis_url: str,
    worker_id: str,
    backoff_seconds: int = 30,
    redis_factory=None,
) -> PaperExecutionRedisScheduleState | None:
    clean_redis_url = redis_url.strip()
    if not clean_redis_url:
        return None
    if redis_factory is None:
        from redis import Redis

        redis_factory = Redis.from_url
    return PaperExecutionRedisScheduleState(
        redis_client=redis_factory(clean_redis_url),
        key_prefix=f"portfolio:paper-execution-worker:{_safe_key_part(worker_id)}",
        backoff_seconds=max(int(backoff_seconds), 1),
    )


def _safe_key_part(value: str) -> str:
    return value.strip().replace(":", "_") or "worker"


if __name__ == "__main__":
    raise SystemExit(main())
