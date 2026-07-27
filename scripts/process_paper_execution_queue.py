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
    build_postgres_paper_execution_worker,
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
        help="Tenant UUID to process. Defaults to PORTFOLIO_TENANT_ID.",
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    tenant_id = args.tenant_id.strip()
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
    if not tenant_id:
        print(
            json.dumps(
                {
                    "status": "error",
                    "reason": "tenant_id_required",
                },
                sort_keys=True,
            )
        )
        return 2

    profile = load_database_runtime_profile(os.environ)
    runner = build_postgres_paper_execution_worker(
        tenant_id=tenant_id,
        database_url=profile.database_url,
        backend=profile.backend,
        worker_id=args.worker_id,
    )

    while True:
        summary = runner.run_until_idle(max_items=args.max_items)
        print(json.dumps(summary.to_dict(), sort_keys=True))
        if not args.daemon:
            return 0
        if summary.idle:
            time.sleep(max(args.idle_sleep_seconds, 0.0))


if __name__ == "__main__":
    raise SystemExit(main())
